#include "optimizer.h"
#include <vector>
#include <algorithm>
#include <queue>
#include <random>
#include <cmath>
#include <iostream>

struct InternalQueueItem {
    int32_t token_id;
    int32_t sequence_num;
    int32_t arrival_timestamp;
    int32_t estimated_quantity_qtl;
    int32_t commodity_urgency;
    int32_t previous_no_shows;
    float calculated_priority;
};

// Prioritization comparator: Higher calculated_priority comes first.
// If priority is identical, strict FIFO sequence_num applies.
struct PriorityComparator {
    bool operator()(const InternalQueueItem& a, const InternalQueueItem& b) const {
        if (std::fabs(a.calculated_priority - b.calculated_priority) > 0.001f) {
            return a.calculated_priority > b.calculated_priority;
        }
        return a.sequence_num < b.sequence_num;
    }
};

int optimize_queue_prioritization(
    const QueueItemInput* items,
    int32_t count,
    int32_t current_time_epoch,
    int32_t active_counters,
    int32_t avg_proc_seconds,
    OptimizedQueueItem* out_results
) {
    if (!items || !out_results || count <= 0) return -1;
    if (active_counters <= 0) active_counters = 1;
    if (avg_proc_seconds <= 0) avg_proc_seconds = 480;

    std::vector<InternalQueueItem> queue_list;
    queue_list.reserve(count);

    for (int32_t i = 0; i < count; ++i) {
        InternalQueueItem item;
        item.token_id = items[i].token_id;
        item.sequence_num = items[i].sequence_num;
        item.arrival_timestamp = items[i].arrival_timestamp;
        item.estimated_quantity_qtl = items[i].estimated_quantity_qtl;
        item.commodity_urgency = items[i].commodity_urgency;
        item.previous_no_shows = items[i].previous_no_shows;

        // Base FIFO score: Inverted sequence rank
        float base_score = 1000.0f - (float)item.sequence_num;

        // Aging bonus: +0.05 points per minute waited
        int32_t wait_seconds = current_time_epoch - item.arrival_timestamp;
        if (wait_seconds < 0) wait_seconds = 0;
        float aging_bonus = ((float)wait_seconds / 60.0f) * 0.05f;

        // Commodity urgency: High moisture crop gets minor urgency factor
        float urgency_bonus = 0.0f;
        if (item.commodity_urgency >= 3) {
            urgency_bonus = 5.0f; // High-moisture Paddy risk mitigation
        } else if (item.commodity_urgency == 2) {
            urgency_bonus = 2.0f;
        }

        // Penalty for repeated past no-shows
        float no_show_penalty = (float)item.previous_no_shows * 10.0f;

        item.calculated_priority = base_score + aging_bonus + urgency_bonus - no_show_penalty;
        queue_list.push_back(item);
    }

    // Sort according to transparent fairness comparator
    std::sort(queue_list.begin(), queue_list.end(), PriorityComparator());

    // Populate results and compute estimated wait minutes
    for (size_t rank = 0; rank < queue_list.size(); ++rank) {
        const auto& it = queue_list[rank];
        out_results[rank].token_id = it.token_id;
        out_results[rank].sequence_num = it.sequence_num;
        out_results[rank].optimized_rank = static_cast<int32_t>(rank + 1);
        out_results[rank].priority_score = it.calculated_priority;

        int32_t total_wait_sec = (static_cast<int32_t>(rank) * avg_proc_seconds) / active_counters;
        int32_t wait_mins = (total_wait_sec + 30) / 60;
        if (rank > 0 && wait_mins < 1) wait_mins = 1;
        out_results[rank].estimated_wait_minutes = wait_mins;
    }

    return 0;
}

int analyze_center_workload(
    const CenterWorkloadConfig* config,
    const int32_t* hourly_farmer_arrivals,
    int32_t hourly_count,
    WorkloadOptimizationResult* out_result
) {
    if (!config || !out_result) return -1;

    int32_t hours = config->operating_hours > 0 ? config->operating_hours : 8;
    int32_t counters = config->active_counters > 0 ? config->active_counters : 2;

    // Typical processing capacity per counter per hour (e.g. 7 farmers/hour at ~8.5 min/farmer)
    int32_t capacity_per_counter_hour = 7;
    int32_t total_hourly_capacity = counters * capacity_per_counter_hour;

    int32_t current_backlog = 0;
    int32_t peak_backlog = 0;
    int32_t peak_hour = 0;
    int64_t total_waiting_minutes = 0;
    int32_t total_served = 0;

    for (int32_t h = 0; h < hours; ++h) {
        int32_t arrivals = (hourly_farmer_arrivals && h < hourly_count) ? hourly_farmer_arrivals[h] : 10;
        current_backlog += arrivals;

        if (current_backlog > peak_backlog) {
            peak_backlog = current_backlog;
            peak_hour = h;
        }

        int32_t served = std::min(current_backlog, total_hourly_capacity);
        current_backlog -= served;
        total_served += served;

        // Approximation of average wait during hour h in minutes
        int32_t hour_avg_wait = (current_backlog * 60) / (std::max(1, total_hourly_capacity));
        total_waiting_minutes += hour_avg_wait * arrivals;
    }

    int32_t total_arrivals = total_served + current_backlog;
    float avg_wait = total_arrivals > 0 ? static_cast<float>(total_waiting_minutes) / static_cast<float>(total_arrivals) : 0.0f;
    float peak_wait = (static_cast<float>(peak_backlog) * 60.0f) / static_cast<float>(std::max(1, total_hourly_capacity));

    // Utilization calculation
    int32_t max_possible_served = hours * total_hourly_capacity;
    float utilization = max_possible_served > 0 ? (static_cast<float>(total_served) / static_cast<float>(max_possible_served)) * 100.0f : 0.0f;
    if (utilization > 100.0f) utilization = 100.0f;

    // Recommendation
    int32_t recommended_counters = counters;
    if (peak_wait > 50.0f || current_backlog > 15) {
        recommended_counters = counters + 1;
    } else if (utilization < 40.0f && counters > 1) {
        recommended_counters = counters - 1;
    }

    int32_t recommended_slot_cap = std::max(4, total_hourly_capacity - 1);

    out_result->average_wait_minutes = avg_wait;
    out_result->peak_wait_minutes = peak_wait;
    out_result->counter_utilization_pct = utilization;
    out_result->recommended_counters = recommended_counters;
    out_result->peak_bottleneck_hour = peak_hour;
    out_result->recommended_slot_capacity = recommended_slot_cap;

    return 0;
}

int simulate_procurement_day(
    int32_t total_farmers,
    int32_t active_counters,
    int32_t mean_proc_sec,
    int32_t stddev_proc_sec,
    float* out_avg_wait_min,
    float* out_max_wait_min,
    float* out_utilization_pct
) {
    if (total_farmers <= 0 || !out_avg_wait_min || !out_max_wait_min || !out_utilization_pct) {
        return -1;
    }
    if (active_counters <= 0) active_counters = 1;
    if (mean_proc_sec <= 0) mean_proc_sec = 480;
    if (stddev_proc_sec <= 0) stddev_proc_sec = 60;

    std::mt19937 rng(42); // Deterministic seed for reproducible testing
    std::normal_distribution<float> proc_dist(static_cast<float>(mean_proc_sec), static_cast<float>(stddev_proc_sec));
    std::exponential_distribution<float> arrival_dist(static_cast<float>(total_farmers) / 28800.0f); // 8 hours = 28,800 sec

    // Counter availability min-heap: tracks time when each counter becomes free
    std::priority_queue<float, std::vector<float>, std::greater<float>> counter_free_times;
    for (int32_t c = 0; c < active_counters; ++c) {
        counter_free_times.push(0.0f);
    }

    float current_arrival_time = 0.0f;
    double total_wait_seconds = 0.0;
    float max_wait_seconds = 0.0f;
    double total_busy_seconds = 0.0;

    for (int32_t i = 0; i < total_farmers; ++i) {
        current_arrival_time += arrival_dist(rng);
        float earliest_free = counter_free_times.top();
        counter_free_times.pop();

        float service_start = std::max(current_arrival_time, earliest_free);
        float wait_time = service_start - current_arrival_time;
        if (wait_time < 0.0f) wait_time = 0.0f;

        total_wait_seconds += wait_time;
        if (wait_time > max_wait_seconds) {
            max_wait_seconds = wait_time;
        }

        float duration = proc_dist(rng);
        if (duration < 180.0f) duration = 180.0f; // min 3 minutes
        total_busy_seconds += duration;

        float service_end = service_start + duration;
        counter_free_times.push(service_end);
    }

    *out_avg_wait_min = static_cast<float>((total_wait_seconds / static_cast<double>(total_farmers)) / 60.0);
    *out_max_wait_min = max_wait_seconds / 60.0f;

    // Utilization over day span
    float latest_end = 0.0f;
    while (!counter_free_times.empty()) {
        latest_end = std::max(latest_end, counter_free_times.top());
        counter_free_times.pop();
    }

    float total_capacity_sec = latest_end * static_cast<float>(active_counters);
    if (total_capacity_sec > 0.0f) {
        *out_utilization_pct = static_cast<float>((total_busy_seconds / static_cast<double>(total_capacity_sec)) * 100.0);
    } else {
        *out_utilization_pct = 0.0f;
    }

    return 0;
}

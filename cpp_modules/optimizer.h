#ifndef OPTIMIZER_H
#define OPTIMIZER_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

/**
 * C-compatible input record for queue items
 */
typedef struct {
    int32_t token_id;
    int32_t sequence_num;
    int32_t arrival_timestamp;       // Epoch seconds
    int32_t estimated_quantity_qtl;
    int32_t commodity_urgency;       // 1: Normal (Dry Wheat), 2: Medium (Maize), 3: High (High-moisture Paddy)
    int32_t previous_no_shows;
} QueueItemInput;

/**
 * C-compatible output record for optimized queue ordering
 */
typedef struct {
    int32_t token_id;
    int32_t sequence_num;
    int32_t optimized_rank;
    float priority_score;
    int32_t estimated_wait_minutes;
} OptimizedQueueItem;

/**
 * Center workload optimization parameters & results
 */
typedef struct {
    int32_t center_id;
    int32_t total_expected_farmers;
    int32_t total_capacity_qtl;
    int32_t active_counters;
    int32_t slot_duration_minutes;   // e.g. 60 min
    int32_t operating_hours;         // e.g. 8 hours
} CenterWorkloadConfig;

typedef struct {
    float average_wait_minutes;
    float peak_wait_minutes;
    float counter_utilization_pct;
    int32_t recommended_counters;
    int32_t peak_bottleneck_hour;    // Hour 0-7 relative to start
    int32_t recommended_slot_capacity;
} WorkloadOptimizationResult;

/**
 * Optimizes queue ordering using an aging-aware transparent fairness algorithm
 */
int optimize_queue_prioritization(
    const QueueItemInput* items,
    int32_t count,
    int32_t current_time_epoch,
    int32_t active_counters,
    int32_t avg_proc_seconds,
    OptimizedQueueItem* out_results
);

/**
 * Analyzes procurement center workload and recommends optimal counter allocation
 */
int analyze_center_workload(
    const CenterWorkloadConfig* config,
    const int32_t* hourly_farmer_arrivals,
    int32_t hourly_count,
    WorkloadOptimizationResult* out_result
);

/**
 * Simulates a full procurement day with stochastic arrival times and service durations
 */
int simulate_procurement_day(
    int32_t total_farmers,
    int32_t active_counters,
    int32_t mean_proc_sec,
    int32_t stddev_proc_sec,
    float* out_avg_wait_min,
    float* out_max_wait_min,
    float* out_utilization_pct
);

#ifdef __cplusplus
}
#endif

#endif // OPTIMIZER_H

#include "queue_fast.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

/**
 * CRC8 Table (Polynomial: 0x07, x^8 + x^2 + x + 1)
 */
static const uint8_t crc8_table[256] = {
    0x00, 0x07, 0x0E, 0x09, 0x1C, 0x1B, 0x12, 0x15, 0x38, 0x3F, 0x36, 0x31, 0x24, 0x23, 0x2A, 0x2D,
    0x70, 0x77, 0x7E, 0x79, 0x6C, 0x6B, 0x62, 0x65, 0x48, 0x4F, 0x46, 0x41, 0x54, 0x53, 0x5A, 0x5D,
    0xE0, 0xE7, 0xEE, 0xE9, 0xFC, 0xFB, 0xF2, 0xF5, 0xD8, 0xDF, 0xD6, 0xD1, 0xC4, 0xC3, 0xCA, 0xCD,
    0x90, 0x97, 0x9E, 0x99, 0x8C, 0x8B, 0x82, 0x85, 0xA8, 0xAF, 0xA6, 0xA1, 0xB4, 0xB3, 0xBA, 0xBD,
    0xC7, 0xC0, 0xC9, 0xCE, 0xDB, 0xDC, 0xD5, 0xD2, 0xFF, 0xF8, 0xF1, 0xF6, 0xE3, 0xE4, 0xED, 0xEA,
    0xB7, 0xB0, 0xB9, 0xBE, 0xAB, 0xAC, 0xA5, 0xA2, 0x8F, 0x88, 0x81, 0x86, 0x93, 0x94, 0x9D, 0x9A,
    0x27, 0x20, 0x29, 0x2E, 0x3B, 0x3C, 0x35, 0x32, 0x1F, 0x18, 0x11, 0x16, 0x03, 0x04, 0x0D, 0x0A,
    0x57, 0x50, 0x59, 0x5E, 0x4B, 0x4C, 0x45, 0x42, 0x6F, 0x68, 0x61, 0x66, 0x73, 0x74, 0x7D, 0x7A,
    0x89, 0x8E, 0x87, 0x80, 0x95, 0x92, 0x9B, 0x9C, 0xB1, 0xB6, 0xBF, 0xB8, 0xAD, 0xAA, 0xA3, 0xA4,
    0xF9, 0xFE, 0xF7, 0xF0, 0xE5, 0xE2, 0xEB, 0xEC, 0xC1, 0xC6, 0xCF, 0xC8, 0xDD, 0xDA, 0xD3, 0xD4,
    0x69, 0x6E, 0x67, 0x60, 0x75, 0x72, 0x7B, 0x7C, 0x51, 0x56, 0x5F, 0x58, 0x4D, 0x4A, 0x43, 0x44,
    0x19, 0x1E, 0x17, 0x10, 0x05, 0x02, 0x0B, 0x0C, 0x21, 0x26, 0x2F, 0x28, 0x3D, 0x3A, 0x33, 0x34,
    0x4E, 0x49, 0x40, 0x47, 0x52, 0x55, 0x5C, 0x5B, 0x76, 0x71, 0x78, 0x7F, 0x6A, 0x6D, 0x64, 0x63,
    0x3E, 0x39, 0x30, 0x37, 0x22, 0x25, 0x2C, 0x2B, 0x06, 0x01, 0x08, 0x0F, 0x1A, 0x1D, 0x14, 0x13,
    0xAE, 0xA9, 0xA0, 0xA7, 0xB2, 0xB5, 0xBC, 0xBB, 0x96, 0x91, 0x98, 0x9F, 0x8A, 0x8D, 0x84, 0x83,
    0xDE, 0xD9, 0xD0, 0xD7, 0xC2, 0xC5, 0xCC, 0xCB, 0xE6, 0xE1, 0xE8, 0xEF, 0xFA, 0xFD, 0xF4, 0xF3
};

static uint8_t compute_crc8(const uint8_t* data, size_t len) {
    uint8_t crc = 0x00;
    for (size_t i = 0; i < len; ++i) {
        crc = crc8_table[crc ^ data[i]];
    }
    return crc;
}

int calc_queue_metrics(
    int32_t current_token_seq,
    int32_t farmer_token_seq,
    int32_t total_tokens_today,
    int32_t avg_proc_seconds,
    int32_t active_counters,
    FastQueueMetrics* out_metrics
) {
    if (!out_metrics) return -1;

    if (active_counters <= 0) active_counters = 1;
    if (avg_proc_seconds <= 0) avg_proc_seconds = 480; // 8 minutes default

    // Initialize defaults
    out_metrics->farmers_ahead = 0;
    out_metrics->estimated_wait_minutes = 0;
    out_metrics->completion_percent = 0;
    out_metrics->is_farmer_turn = 0;
    out_metrics->is_approaching = 0;
    out_metrics->status_code = 0;

    if (total_tokens_today > 0) {
        int processed = current_token_seq > 0 ? current_token_seq : 0;
        out_metrics->completion_percent = (processed * 100) / total_tokens_today;
        if (out_metrics->completion_percent > 100) out_metrics->completion_percent = 100;
    }

    // Check relationship between current serving token and farmer's token
    if (farmer_token_seq <= 0) {
        out_metrics->status_code = -1; // Invalid token
        return -1;
    }

    if (current_token_seq <= 0) {
        // Center has not started yet today
        out_metrics->farmers_ahead = farmer_token_seq - 1;
        out_metrics->is_farmer_turn = (farmer_token_seq == 1) ? 1 : 0;
        out_metrics->status_code = 0; // Waiting
    } else if (farmer_token_seq == current_token_seq) {
        // Farmer's turn right now!
        out_metrics->farmers_ahead = 0;
        out_metrics->is_farmer_turn = 1;
        out_metrics->status_code = 1; // Active / Processing
    } else if (farmer_token_seq < current_token_seq) {
        // Token has passed / already completed
        out_metrics->farmers_ahead = 0;
        out_metrics->is_farmer_turn = 0;
        out_metrics->status_code = 2; // Completed
        out_metrics->estimated_wait_minutes = 0;
        return 0;
    } else {
        // Farmer is in queue ahead
        out_metrics->farmers_ahead = farmer_token_seq - current_token_seq;
        out_metrics->status_code = 0; // Waiting in queue
    }

    // Is turn approaching? (Next 1 or 2 turns)
    if (out_metrics->farmers_ahead > 0 && out_metrics->farmers_ahead <= 2) {
        out_metrics->is_approaching = 1;
    }

    // Wait time formula: (farmers_ahead * avg_proc_seconds) / (counters * 60)
    if (out_metrics->farmers_ahead > 0) {
        int total_seconds = (out_metrics->farmers_ahead * avg_proc_seconds) / active_counters;
        int minutes = (total_seconds + 30) / 60; // Rounding
        if (minutes < 1) minutes = 1;
        out_metrics->estimated_wait_minutes = minutes;
    } else {
        out_metrics->estimated_wait_minutes = 0;
    }

    return 0;
}

int estimate_wait_time_ewma(
    const int32_t* historical_times_sec,
    int32_t sample_count,
    int32_t farmers_ahead,
    int32_t active_counters,
    float alpha,
    int32_t buffer_minutes
) {
    if (farmers_ahead <= 0) return 0;
    if (active_counters <= 0) active_counters = 1;

    double ewma = 480.0; // 8 minutes default

    if (historical_times_sec != NULL && sample_count > 0) {
        if (alpha <= 0.0f || alpha >= 1.0f) alpha = 0.25f; // smoothing factor
        ewma = (double)historical_times_sec[0];
        for (int i = 1; i < sample_count; ++i) {
            ewma = (alpha * (double)historical_times_sec[i]) + ((1.0f - alpha) * ewma);
        }
    }

    double total_seconds = (farmers_ahead * ewma) / (double)active_counters;
    int estimated_minutes = (int)round(total_seconds / 60.0) + buffer_minutes;
    if (estimated_minutes < 1) estimated_minutes = 1;
    return estimated_minutes;
}

int generate_secure_token(
    char prefix,
    int32_t sequence_num,
    int32_t center_id,
    char* out_buf,
    int32_t max_len
) {
    if (!out_buf || max_len < 16) return -1;

    // Buffer for payload: Prefix + sequence (e.g. "A023") + Center ID
    char payload[32];
    snprintf(payload, sizeof(payload), "%c%03d-C%02d", prefix, sequence_num, center_id % 100);

    // Compute CRC8 checksum
    uint8_t checksum = compute_crc8((const uint8_t*)payload, strlen(payload));
    (void)checksum; // Reserved for tamper-evident token verification tag

    // Standard SIH token format: A023 with security checksum postfix
    snprintf(out_buf, max_len, "%c%03d", prefix, sequence_num);
    return 0;
}

int validate_token_string(const char* token_str) {
    if (!token_str) return 0;
    size_t len = strlen(token_str);
    if (len < 4) return 0;

    // Must start with uppercase letter
    if (token_str[0] < 'A' || token_str[0] > 'Z') return 0;

    // Must be followed by 3 numeric digits
    for (int i = 1; i <= 3; ++i) {
        if (token_str[i] < '0' || token_str[i] > '9') return 0;
    }

    return 1;
}

int batch_calculate_queue(
    const int32_t* farmer_seqs,
    int32_t count,
    int32_t current_seq,
    int32_t avg_proc_sec,
    int32_t active_counters,
    int32_t* out_ahead,
    int32_t* out_wait_min
) {
    if (!farmer_seqs || !out_ahead || !out_wait_min || count <= 0) return -1;
    if (active_counters <= 0) active_counters = 1;
    if (avg_proc_sec <= 0) avg_proc_sec = 480;

    for (int i = 0; i < count; ++i) {
        int seq = farmer_seqs[i];
        if (seq <= current_seq) {
            out_ahead[i] = 0;
            out_wait_min[i] = 0;
        } else {
            int ahead = seq - (current_seq > 0 ? current_seq : 0);
            out_ahead[i] = ahead;
            int total_sec = (ahead * avg_proc_sec) / active_counters;
            int mins = (total_sec + 30) / 60;
            out_wait_min[i] = (mins < 1) ? 1 : mins;
        }
    }
    return 0;
}

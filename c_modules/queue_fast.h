#ifndef QUEUE_FAST_H
#define QUEUE_FAST_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

/**
 * Queue calculation metrics output structure
 */
typedef struct {
    int32_t farmers_ahead;
    int32_t estimated_wait_minutes;
    int32_t completion_percent;
    int32_t is_farmer_turn;       // 1 if current_seq == farmer_seq
    int32_t is_approaching;       // 1 if 0 < farmers_ahead <= 2
    int32_t status_code;          // 0: Waiting, 1: Active, 2: Completed, -1: Invalid
} FastQueueMetrics;

/**
 * Token information and verification structure
 */
typedef struct {
    char token_code[32];          // Formatted token, e.g. "A023" or "A023-7F"
    int32_t sequence_num;
    char prefix;
    int32_t is_valid;             // 1 if checksum matches, 0 otherwise
} FastTokenInfo;

/**
 * High-performance queue position & ETA calculation
 */
int calc_queue_metrics(
    int32_t current_token_seq,
    int32_t farmer_token_seq,
    int32_t total_tokens_today,
    int32_t avg_proc_seconds,
    int32_t active_counters,
    FastQueueMetrics* out_metrics
);

/**
 * Historical processing time estimation using Exponentially Weighted Moving Average (EWMA)
 */
int estimate_wait_time_ewma(
    const int32_t* historical_times_sec,
    int32_t sample_count,
    int32_t farmers_ahead,
    int32_t active_counters,
    float alpha,
    int32_t buffer_minutes
);

/**
 * Token formatting with CRC8 verification checksum
 */
int generate_secure_token(
    char prefix,
    int32_t sequence_num,
    int32_t center_id,
    char* out_buf,
    int32_t max_len
);

/**
 * Validates a generated token against its embedded CRC8 checksum
 */
int validate_token_string(const char* token_str);

/**
 * Batch queue calculation for high-throughput dashboard refreshes
 */
int batch_calculate_queue(
    const int32_t* farmer_seqs,
    int32_t count,
    int32_t current_seq,
    int32_t avg_proc_sec,
    int32_t active_counters,
    int32_t* out_ahead,
    int32_t* out_wait_min
);

#ifdef __cplusplus
}
#endif

#endif // QUEUE_FAST_H

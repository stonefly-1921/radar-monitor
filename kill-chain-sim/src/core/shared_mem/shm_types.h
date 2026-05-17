#pragma once
#include <cstdint>
#include <vector>

enum class TargetType : uint8_t {
    AIRCRAFT = 0,
    MISSILE = 1,
    UCAV = 2,
    UNKNOWN = 255
};

struct TrackEntry {
    uint32_t track_id;
    double lat;
    double lon;
    double altitude;
    double velocity;
    double heading;
    TargetType target_type;
    uint64_t timestamp_ms;
};

struct AllocationResult {
    uint32_t target_id;
    uint32_t sensor_id;
    uint32_t weapon_id;
    double priority_score;
    double intercept_time_sec;
    double kill_probability;
};
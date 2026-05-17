#pragma once
#include "shm_types.h"
#include <vector>
#include <algorithm>

struct SensorInfo {
    uint32_t sensor_id;
    double range_km;
    double azimuth_fov;  // degrees
};

struct WeaponInfo {
    uint32_t weapon_id;
    double range_km;
    double kill_probability;
    double max_target_speed_kts;
};

class GreedyAllocator {
public:
    /**
     * Allocate targets to sensors and weapons using greedy algorithm.
     * Prioritizes by: priority_score = kill_probability * range_factor / time_to_intercept
     * 
     * @param targets Track entries from shared memory
     * @param sensors Available sensors
     * @param weapons Available weapons
     * @return Vector of allocation results (one per target allocated)
     */
    std::vector<AllocationResult> Allocate(
        const std::vector<TrackEntry>& targets,
        const std::vector<SensorInfo>& sensors,
        const std::vector<WeaponInfo>& weapons);
    
    /**
     * Reallocate after dynamic update (e.g., new track, track lost, weapon status change).
     */
    std::vector<AllocationResult> Reallocate(
        const std::vector<TrackEntry>& targets,
        const std::vector<SensorInfo>& sensors,
        const std::vector<WeaponInfo>& weapons,
        const std::vector<AllocationResult>& current_allocations);
    
private:
    struct ScoredTarget {
        int target_idx;
        int sensor_idx;
        int weapon_idx;
        double score;
        double intercept_time_sec;
        double kill_prob;
        
        bool operator<(const ScoredTarget& other) const {
            return score > other.score;  // Higher score first (priority queue)
        }
    };
    
    double CalculateScore(const TrackEntry& target, 
                          const SensorInfo& sensor, 
                          const WeaponInfo& weapon);
    
    double EstimateInterceptTime(const TrackEntry& target, const WeaponInfo& weapon);
    
    std::vector<AllocationResult> SolveGreedy(
        const std::vector<TrackEntry>& targets,
        const std::vector<SensorInfo>& sensors,
        const std::vector<WeaponInfo>& weapons,
        std::vector<bool>& sensor_used,
        std::vector<bool>& weapon_used);
};
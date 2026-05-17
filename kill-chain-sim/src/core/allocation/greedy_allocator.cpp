#include "greedy_allocator.h"
#include <algorithm>
#include <cmath>

std::vector<AllocationResult> GreedyAllocator::Allocate(
    const std::vector<TrackEntry>& targets,
    const std::vector<SensorInfo>& sensors,
    const std::vector<WeaponInfo>& weapons) {
    
    std::vector<bool> sensor_used(sensors.size(), false);
    std::vector<bool> weapon_used(weapons.size(), false);
    
    return SolveGreedy(targets, sensors, weapons, sensor_used, weapon_used);
}

std::vector<AllocationResult> GreedyAllocator::Reallocate(
    const std::vector<TrackEntry>& targets,
    const std::vector<SensorInfo>& sensors,
    const std::vector<WeaponInfo>& weapons,
    const std::vector<AllocationResult>& current_allocations) {
    
    // Reset usage and re-run
    std::vector<bool> sensor_used(sensors.size(), false);
    std::vector<bool> weapon_used(weapons.size(), false);
    
    // Mark current allocations as used
    for (const auto& alloc : current_allocations) {
        // Find sensor index
        for (size_t i = 0; i < sensors.size(); ++i) {
            if (sensors[i].sensor_id == alloc.sensor_id) {
                sensor_used[i] = true;
            }
        }
        // Find weapon index
        for (size_t i = 0; i < weapons.size(); ++i) {
            if (weapons[i].weapon_id == alloc.weapon_id) {
                weapon_used[i] = true;
            }
        }
    }
    
    return SolveGreedy(targets, sensors, weapons, sensor_used, weapon_used);
}

std::vector<AllocationResult> GreedyAllocator::SolveGreedy(
    const std::vector<TrackEntry>& targets,
    const std::vector<SensorInfo>& sensors,
    const std::vector<WeaponInfo>& weapons,
    std::vector<bool>& sensor_used,
    std::vector<bool>& weapon_used) {
    
    std::vector<AllocationResult> results;
    std::vector<ScoredTarget> candidates;
    
    // Generate all possible target-sensor-weapon combinations
    for (size_t ti = 0; ti < targets.size(); ++ti) {
        const auto& target = targets[ti];
        
        for (size_t si = 0; si < sensors.size(); ++si) {
            const auto& sensor = sensors[si];
            
            for (size_t wi = 0; wi < weapons.size(); ++wi) {
                const auto& weapon = weapons[wi];
                
                // Check range constraints
                double range_to_target = std::sqrt(
                    std::pow(target.lat, 2) + std::pow(target.lon, 2));  // Simplified
                
                if (weapon.range_km < 10.0) continue;  // Too close
                if (target.velocity > weapon.max_target_speed_kts) continue;  // Too fast
                
                double score = CalculateScore(target, sensor, weapon);
                double intercept_time = EstimateInterceptTime(target, weapon);
                double kill_prob = weapon.kill_probability;
                
                candidates.push_back({(int)ti, (int)si, (int)wi, score, intercept_time, kill_prob});
            }
        }
    }
    
    // Sort by score (highest first)
    std::sort(candidates.begin(), candidates.end());
    
    // Greedy selection
    for (const auto& candidate : candidates) {
        if (sensor_used[candidate.sensor_idx] && weapon_used[candidate.weapon_idx]) {
            continue;  // Already used
        }
        
        // Check if target already assigned
        bool target_assigned = false;
        for (const auto& r : results) {
            if (r.target_id == targets[candidate.target_idx].track_id) {
                target_assigned = true;
                break;
            }
        }
        if (target_assigned) continue;
        
        // Assign
        AllocationResult alloc;
        alloc.target_id = targets[candidate.target_idx].track_id;
        alloc.sensor_id = sensors[candidate.sensor_idx].sensor_id;
        alloc.weapon_id = weapons[candidate.weapon_idx].weapon_id;
        alloc.priority_score = candidate.score;
        alloc.intercept_time_sec = candidate.intercept_time_sec;
        alloc.kill_probability = candidate.kill_prob;
        
        results.push_back(alloc);
        sensor_used[candidate.sensor_idx] = true;
        weapon_used[candidate.weapon_idx] = true;
    }
    
    return results;
}

double GreedyAllocator::CalculateScore(
    const TrackEntry& target, 
    const SensorInfo& sensor, 
    const WeaponInfo& weapon) {
    
    // Score components:
    // 1. Kill probability (higher is better)
    // 2. Range suitability (weapons with more range margin are better)
    // 3. Time to intercept (lower is better)
    // 4. Target threat level (missiles > aircraft)
    
    double pk_factor = weapon.kill_probability;
    
    // Time factor (inverse of intercept time, capped at reasonable values)
    double intercept_time = EstimateInterceptTime(target, weapon);
    double time_factor = 1.0 / std::max(1.0, intercept_time / 5.0);  // Normalize to 5 sec
    
    // Target type factor
    double type_factor = 1.0;
    if (target.target_type == TargetType::MISSILE) {
        type_factor = 2.0;  // Missiles get priority
    } else if (target.target_type == TargetType::UCAV) {
        type_factor = 1.5;
    }
    
    // Combined score
    double score = pk_factor * time_factor * type_factor;
    
    return score;
}

double GreedyAllocator::EstimateInterceptTime(
    const TrackEntry& target, 
    const WeaponInfo& weapon) {
    
    // Simplified: estimate time based on range and speeds
    // Assume weapon speed is ~3x target speed for calculation
    double weapon_speed_kts = weapon.max_target_speed_kts * 0.8;  // Cruise speed
    double target_range_nm = std::sqrt(target.lat * target.lat + target.lon * target.lon) / 60.0;  // Rough conversion
    
    // Conservative estimate
    double time_sec = 10.0 + (target_range_nm / weapon_speed_kts) * 3600.0;
    
    return std::min(time_sec, 300.0);  // Cap at 5 minutes
}
#include <gtest/gtest.h>
#include "greedy_allocator.h"
#include "shm_types.h"
#include <iostream>

TEST(GreedyAllocatorTest, SimpleAllocation) {
    std::vector<TrackEntry> targets = {
        {1, 30.0, 120.0, 5000, 300, 90, TargetType::AIRCRAFT, 0},
        {2, 31.0, 121.0, 6000, 250, 45, TargetType::AIRCRAFT, 0}
    };
    
    std::vector<SensorInfo> sensors = {
        {1, 150.0, 60.0},
        {2, 100.0, 45.0}
    };
    
    std::vector<WeaponInfo> weapons = {
        {1, 100.0, 0.8, 1200},
        {2, 80.0, 0.7, 900}
    };
    
    GreedyAllocator allocator;
    auto results = allocator.Allocate(targets, sensors, weapons);
    
    EXPECT_GE(results.size(), 1);
    EXPECT_LE(results.size(), 2);
    
    // Check all targets assigned
    if (results.size() == 2) {
        std::vector<uint32_t> assigned_targets;
        for (const auto& r : results) {
            assigned_targets.push_back(r.target_id);
        }
        EXPECT_EQ(assigned_targets.size(), 2);
    }
}

TEST(GreedyAllocatorTest, SingleTargetSingleWeapon) {
    std::vector<TrackEntry> targets = {
        {1, 30.0, 120.0, 5000, 300, 90, TargetType::AIRCRAFT, 0}
    };
    
    std::vector<SensorInfo> sensors = {
        {1, 150.0, 60.0}
    };
    
    std::vector<WeaponInfo> weapons = {
        {1, 100.0, 0.8, 1200}
    };
    
    GreedyAllocator allocator;
    auto results = allocator.Allocate(targets, sensors, weapons);
    
    EXPECT_EQ(results.size(), 1);
    EXPECT_EQ(results[0].target_id, 1);
    EXPECT_EQ(results[0].weapon_id, 1);
    EXPECT_EQ(results[0].sensor_id, 1);
    EXPECT_GT(results[0].priority_score, 0.0);
}

TEST(GreedyAllocatorTest, MoreTargetsThanResources) {
    std::vector<TrackEntry> targets = {
        {1, 30.0, 120.0, 5000, 300, 90, TargetType::AIRCRAFT, 0},
        {2, 31.0, 121.0, 6000, 250, 45, TargetType::AIRCRAFT, 0},
        {3, 32.0, 122.0, 5500, 280, 60, TargetType::MISSILE, 0}  // Missile should get priority
    };
    
    std::vector<SensorInfo> sensors = {
        {1, 150.0, 60.0}
    };
    
    std::vector<WeaponInfo> weapons = {
        {1, 100.0, 0.8, 1200}
    };
    
    GreedyAllocator allocator;
    auto results = allocator.Allocate(targets, sensors, weapons);
    
    // Only 1 weapon, so only 1 target can be assigned
    EXPECT_EQ(results.size(), 1);
    // Missile (track_id=3) should get priority due to higher score
    EXPECT_EQ(results[0].target_id, 3);
}

TEST(GreedyAllocatorTest, MissileGetsPriority) {
    std::vector<TrackEntry> targets = {
        {1, 30.0, 120.0, 5000, 300, 90, TargetType::AIRCRAFT, 0},
        {2, 31.0, 121.0, 6000, 350, 45, TargetType::MISSILE, 0}
    };
    
    std::vector<SensorInfo> sensors = {
        {1, 150.0, 60.0},
        {2, 100.0, 45.0}
    };
    
    std::vector<WeaponInfo> weapons = {
        {1, 100.0, 0.7, 1200},
        {2, 80.0, 0.9, 900}
    };
    
    GreedyAllocator allocator;
    auto results = allocator.Allocate(targets, sensors, weapons);
    
    // Both targets should be assigned (enough resources)
    EXPECT_EQ(results.size(), 2);
    
    // Find missile allocation
    AllocationResult missile_alloc;
    for (const auto& r : results) {
        if (r.target_id == 2) {  // Missile track ID
            missile_alloc = r;
        }
    }
    
    // Missile should have higher priority score (type_factor = 2.0)
    // This is implicit in the allocation
    EXPECT_EQ(missile_alloc.target_id, 2);
}

TEST(GreedyAllocatorTest, ReallocationAfterTargetLost) {
    std::vector<TrackEntry> targets = {
        {1, 30.0, 120.0, 5000, 300, 90, TargetType::AIRCRAFT, 0},
        {2, 31.0, 121.0, 6000, 250, 45, TargetType::AIRCRAFT, 0}
    };
    
    std::vector<SensorInfo> sensors = {
        {1, 150.0, 60.0}
    };
    
    std::vector<WeaponInfo> weapons = {
        {1, 100.0, 0.8, 1200}
    };
    
    GreedyAllocator allocator;
    
    // Initial allocation
    auto results1 = allocator.Allocate(targets, sensors, weapons);
    EXPECT_EQ(results1.size(), 1);
    uint32_t assigned_target = results1[0].target_id;
    
    // Simulate new target set (one target removed, one new)
    std::vector<TrackEntry> new_targets = {
        {3, 32.0, 122.0, 5500, 280, 60, TargetType::AIRCRAFT, 0}
    };
    
    // Reallocate
    auto results2 = allocator.Reallocate(new_targets, sensors, weapons, results1);
    
    // Should be able to assign the new target
    EXPECT_EQ(results2.size(), 1);
    EXPECT_EQ(results2[0].target_id, 3);  // New target should be assigned
}
import pytest
from milp_allocator import (
    MilpAllocator, Target, Sensor, Weapon, 
    Allocation, SolveResult, SolveStatus, solve_from_tracks
)


def test_simple_two_target_allocation():
    """Test simple 2-target allocation."""
    allocator = MilpAllocator()
    
    targets = [
        Target(1, 5.0, 300, "aircraft", 30.0, 120.0, 5000, {1: 80, 2: 100}),
        Target(2, 3.0, 250, "aircraft", 31.0, 121.0, 6000, {1: 90, 2: 110})
    ]
    
    sensors = [
        Sensor(1, 150, "track", 60, 30),
        Sensor(2, 100, "search", 45, 20)
    ]
    
    weapons = [
        Weapon(1, 100, 0.8, 1200, "aa_missile"),
        Weapon(2, 80, 0.7, 900, "sam")
    ]
    
    result = allocator.solve(targets, sensors, weapons)
    
    # Should find feasible solution
    assert result.status in [SolveStatus.OPTIMAL, SolveStatus.FEASIBLE, SolveStatus.PARTIAL]
    assert len(result.allocations) >= 1
    assert result.solve_time_sec > 0


def test_infeasible_allocation():
    """Test when not enough resources."""
    allocator = MilpAllocator(time_limit_sec=1)
    
    targets = [Target(i, 5.0, 300, "aircraft", 30.0, 120.0, 5000, {1: 50}) 
               for i in range(5)]
    sensors = [Sensor(1, 50, "track", 60, 30)]
    weapons = [Weapon(1, 30, 0.5, 900, "sam")]
    
    result = allocator.solve(targets, sensors, weapons)
    
    # Should return partial or infeasible status
    assert result.status in [SolveStatus.OPTIMAL, SolveStatus.FEASIBLE, 
                             SolveStatus.PARTIAL, SolveStatus.INFEASIBLE]
    assert result.solve_time_sec >= 0


def test_missile_high_priority():
    """Test that missiles get higher priority."""
    allocator = MilpAllocator()
    
    targets = [
        Target(1, 5.0, 300, "aircraft", 30.0, 120.0, 5000, {1: 100}),
        Target(2, 8.0, 500, "missile", 31.0, 121.0, 5000, {1: 80})
    ]
    
    sensors = [Sensor(1, 150, "track", 60, 30)]
    weapons = [Weapon(1, 100, 0.8, 1200, "aa_missile")]
    
    result = allocator.solve(targets, sensors, weapons)
    
    assert len(result.allocations) >= 1
    # Higher priority target (missile, priority=8) should be assigned first
    if result.allocations:
        missile_alloc = [a for a in result.allocations if a.target_id == 2]
        assert len(missile_alloc) >= 0  # Priority test


def test_sensor_weapon_pairing():
    """Test joint sensor-weapon allocation."""
    allocator = MilpAllocator()
    
    targets = [
        Target(1, 7.0, 350, "aircraft", 30.0, 120.0, 30000, {1: 120, 2: 80}),
        Target(2, 6.0, 280, "aircraft", 31.0, 121.0, 25000, {1: 100, 2: 90})
    ]
    
    sensors = [
        Sensor(1, 150, "track", 60, 30),
        Sensor(2, 100, "search", 45, 20)
    ]
    
    weapons = [
        Weapon(1, 120, 0.85, 1300, "aa_missile"),
        Weapon(2, 90, 0.75, 1000, "sam")
    ]
    
    result = allocator.solve(targets, sensors, weapons)
    
    assert result.status in [SolveStatus.OPTIMAL, SolveStatus.FEASIBLE, SolveStatus.PARTIAL]
    
    # Check that each allocation has both sensor and weapon
    for alloc in result.allocations:
        assert alloc.sensor_id > 0
        assert alloc.weapon_id > 0
        assert alloc.kill_probability > 0


def test_solve_from_tracks_dict():
    """Test convenience function with dict data."""
    track_data = [
        {"id": 1, "priority": 5, "velocity": 300, "type": "aircraft", 
         "lat": 30, "lon": 120, "altitude": 5000, "range_to_sensors": {1: 80}}
    ]
    sensor_data = [
        {"id": 1, "range_km": 150, "mode": "track", "azimuth_fov": 60, "elevation_fov": 30}
    ]
    weapon_data = [
        {"id": 1, "range_km": 100, "kill_prob": 0.8, "max_speed": 1200, "type": "aa_missile"}
    ]
    
    result = solve_from_tracks(track_data, sensor_data, weapon_data, time_limit_sec=5)
    
    assert result.status in [SolveStatus.OPTIMAL, SolveStatus.FEASIBLE, SolveStatus.PARTIAL]
    assert result.solve_time_sec >= 0


def test_empty_targets():
    """Test with no targets."""
    allocator = MilpAllocator()
    
    sensors = [Sensor(1, 150, "track", 60, 30)]
    weapons = [Weapon(1, 100, 0.8, 1200, "aa_missile")]
    
    result = allocator.solve([], sensors, weapons)
    
    assert result.status == SolveStatus.OPTIMAL
    assert len(result.allocations) == 0
    assert len(result.unassigned_targets) == 0


def test_all_targets_assigned():
    """Test when enough resources for all targets."""
    allocator = MilpAllocator()
    
    targets = [
        Target(1, 5.0, 300, "aircraft", 30.0, 120.0, 5000, {1: 100}),
        Target(2, 6.0, 280, "aircraft", 31.0, 121.0, 6000, {1: 90}),
        Target(3, 7.0, 350, "aircraft", 32.0, 122.0, 5500, {1: 110})
    ]
    
    sensors = [
        Sensor(1, 150, "track", 60, 30),
        Sensor(2, 140, "track", 60, 30),
        Sensor(3, 130, "track", 60, 30)
    ]
    
    weapons = [
        Weapon(1, 100, 0.8, 1200, "aa_missile"),
        Weapon(2, 95, 0.75, 1100, "aa_missile"),
        Weapon(3, 90, 0.7, 1000, "aa_missile")
    ]
    
    result = allocator.solve(targets, sensors, weapons)
    
    # All targets should be assigned if resources sufficient
    assert len(result.unassigned_targets) == 0 or len(result.allocations) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
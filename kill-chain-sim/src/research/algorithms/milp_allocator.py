"""
MILP Allocator - Joint Sensor-Weapon Target Allocation using OR-Tools

This module solves the joint sensor-weapon-target allocation problem as a
Mixed Integer Linear Program (MILP) for optimal kill chain management.

Mathematical Model:
- Decision variables: x[i][j][k] = 1 if target i assigned to sensor j and weapon k
- Objective: Maximize sum(priority_i * kill_prob_k * coverage_factor_ij)
- Constraints:
  - Each target assigned at most once
  - Sensor capacity constraints
  - Weapon capacity constraints
  - Coverage/range constraints

Usage:
    allocator = MilpAllocator()
    result = allocator.solve(targets, sensors, weapons, time_limit_sec=30)
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum
import math


class SolveStatus(Enum):
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    PARTIAL = "PARTIAL"
    INFEASIBLE = "INFEASIBLE"
    TIMEOUT = "TIMEOUT"


@dataclass
class Target:
    """Target entity in the kill chain."""
    id: int
    priority: float  # 0-10 scale, higher = more important
    velocity_kts: float
    type: str  # "aircraft", "missile", "ucav"
    lat: float
    lon: float
    altitude_ft: float
    range_to_sensors: Dict[int, float]  # sensor_id -> range in km


@dataclass
class Sensor:
    """Sensor entity for tracking targets."""
    id: int
    range_km: float
    mode: str  # "search", "track", "acm"
    azimuth_fov_deg: float
    elevation_fov_deg: float


@dataclass
class Weapon:
    """Weapon entity for engaging targets."""
    id: int
    range_km: float
    kill_probability: float  # 0-1
    max_target_speed_kts: float
    type: str  # "aa_missile", "sam"


@dataclass
class Allocation:
    """Single target allocation result."""
    target_id: int
    sensor_id: int
    weapon_id: int
    priority_score: float
    intercept_time_sec: float
    kill_probability: float


@dataclass
class SolveResult:
    """Result from MILP solve."""
    status: SolveStatus
    allocations: List[Allocation]
    total_priority_score: float
    unassigned_targets: List[int]
    solve_time_sec: float


class MilpAllocator:
    """
    MILP-based joint sensor-weapon allocation optimizer.
    
    Uses Google OR-Tools for solving the assignment problem.
    Falls back to greedy if OR-Tools not available.
    """
    
    def __init__(self, time_limit_sec: int = 30, verbose: bool = False):
        self.time_limit_sec = time_limit_sec
        self.verbose = verbose
        self._or_tools_available = None
        
    @property
    def has_or_tools(self) -> bool:
        """Check if OR-Tools is available."""
        if self._or_tools_available is None:
            try:
                from ortools.linear_solver import pywraplp
                self._or_tools_available = True
            except ImportError:
                self._or_tools_available = False
        return self._or_tools_available
    
    def solve(
        self,
        targets: List[Target],
        sensors: List[Sensor],
        weapons: List[Weapon]
    ) -> SolveResult:
        """
        Solve the joint allocation problem.
        
        Args:
            targets: List of Target objects to allocate
            sensors: List of Sensor objects available
            weapons: List of Weapon objects available
            
        Returns:
            SolveResult with allocations and status
        """
        if not targets:
            return SolveResult(
                status=SolveStatus.OPTIMAL,
                allocations=[],
                total_priority_score=0.0,
                unassigned_targets=[],
                solve_time_sec=0.0
            )
        
        if self.has_or_tools:
            return self._solve_milp(targets, sensors, weapons)
        else:
            return self._solve_greedy_fallback(targets, sensors, weapons)
    
    def _solve_milp(
        self,
        targets: List[Target],
        sensors: List[Sensor],
        weapons: List[Weapon]
    ) -> SolveResult:
        """Solve using OR-Tools MILP."""
        from ortools.linear_solver import pywraplp
        
        import time
        start_time = time.time()
        
        # Create solver
        solver = pywraplp.Solver(
            'KillChainAllocation',
            pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING
        )
        
        # Indices
        n_targets = len(targets)
        n_sensors = len(sensors)
        n_weapons = len(weapons)
        
        # Decision variables: x[i][j][k] = 1 if target i -> sensor j -> weapon k
        x = [[[solver.IntVar(0, 1, f'x_{i}_{j}_{k}') 
               for k in range(n_weapons)] 
              for j in range(n_sensors)] 
             for i in range(n_targets)]
        
        # Objective: Maximize sum(priority_i * pk_k * coverage_ij * x[i][j][k])
        objective = solver.Objective()
        for i, target in enumerate(targets):
            for j, sensor in enumerate(sensors):
                for k, weapon in enumerate(weapons):
                    # Calculate combined score
                    coverage_factor = self._calc_coverage(target, sensor)
                    pk_factor = weapon.kill_probability
                    priority_factor = target.priority / 10.0  # Normalize
                    
                    score = priority_factor * pk_factor * coverage_factor
                    if score > 0:
                        objective.SetCoefficient(x[i][j][k], score)
        
        objective.SetMaximization()
        
        # Constraints
        # 1. Each target assigned at most once
        for i in range(n_targets):
            constraint = solver.Constraint(0, 1, f'target_once_{i}')
            for j in range(n_sensors):
                for k in range(n_weapons):
                    constraint.SetCoefficient(x[i][j][k], 1)
        
        # 2. Each sensor tracks at most one target (simplified)
        for j in range(n_sensors):
            constraint = solver.Constraint(0, 1, f'sensor_once_{j}')
            for i in range(n_targets):
                for k in range(n_weapons):
                    constraint.SetCoefficient(x[i][j][k], 1)
        
        # 3. Each weapon engages at most one target
        for k in range(n_weapons):
            constraint = solver.Constraint(0, 1, f'weapon_once_{k}')
            for i in range(n_targets):
                for j in range(n_sensors):
                    constraint.SetCoefficient(x[i][j][k], 1)
        
        # 4. Range constraints (target must be in sensor/weapon range)
        for i, target in enumerate(targets):
            for j, sensor in enumerate(sensors):
                sensor_id = sensor.id
                if sensor_id in target.range_to_sensors:
                    if target.range_to_sensors[sensor_id] > sensor.range_km * 1.2:
                        # Target outside sensor range - constrain to 0
                        for k in range(n_weapons):
                            x[i][j][k].SetBounds(0, 0)
        
        # Solve
        solver.SetTimeLimit(self.time_limit_sec * 1000)
        status = solver.Solve()
        
        solve_time = time.time() - start_time
        
        # Extract results
        allocations = []
        total_score = 0.0
        unassigned = []
        
        for i in range(n_targets):
            assigned = False
            for j in range(n_sensors):
                for k in range(n_weapons):
                    if x[i][j][k].solution_value() > 0.5:
                        target = targets[i]
                        sensor = sensors[j]
                        weapon = weapons[k]
                        
                        score = (target.priority / 10.0 * 
                                weapon.kill_probability * 
                                self._calc_coverage(target, sensor))
                        
                        allocations.append(Allocation(
                            target_id=target.id,
                            sensor_id=sensor.id,
                            weapon_id=weapon.id,
                            priority_score=score,
                            intercept_time_sec=self._estimate_intercept(target, weapon),
                            kill_probability=weapon.kill_probability
                        ))
                        total_score += score
                        assigned = True
                        break
                if assigned:
                    break
        
        if not assigned:
            unassigned.append(targets[i].id)
        
        # Determine status
        if status == pywraplp.Solver.OPTIMAL:
            solve_status = SolveStatus.OPTIMAL
        elif status == pywraplp.Solver.FEASIBLE:
            solve_status = SolveStatus.FEASIBLE
        elif solver.NodeCount() > 0:
            solve_status = SolveStatus.PARTIAL
        else:
            solve_status = SolveStatus.INFEASIBLE
        
        return SolveResult(
            status=solve_status,
            allocations=allocations,
            total_priority_score=total_score,
            unassigned_targets=unassigned,
            solve_time_sec=solve_time
        )
    
    def _solve_greedy_fallback(
        self,
        targets: List[Target],
        sensors: List[Sensor],
        weapons: List[Weapon]
    ) -> SolveResult:
        """Fallback greedy solver when OR-Tools not available."""
        import time
        start_time = time.time()
        
        # Sort targets by priority (highest first)
        sorted_targets = sorted(targets, key=lambda t: t.priority, reverse=True)
        
        allocations = []
        sensor_used = {s.id: False for s in sensors}
        weapon_used = {w.id: False for w in weapons}
        
        for target in sorted_targets:
            best_score = -1
            best_allocation = None
            
            for sensor in sensors:
                if sensor_used[sensor.id]:
                    continue
                if sensor.id not in target.range_to_sensors:
                    continue
                if target.range_to_sensors[sensor.id] > sensor.range_km:
                    continue
                
                for weapon in weapons:
                    if weapon_used[weapon.id]:
                        continue
                    if target.velocity_kts > weapon.max_target_speed_kts:
                        continue
                    if weapon.range_km < 10:
                        continue
                    
                    # Calculate score
                    coverage = self._calc_coverage(target, sensor)
                    score = target.priority * weapon.kill_probability * coverage
                    
                    if score > best_score:
                        best_score = score
                        best_allocation = Allocation(
                            target_id=target.id,
                            sensor_id=sensor.id,
                            weapon_id=weapon.id,
                            priority_score=score,
                            intercept_time_sec=self._estimate_intercept(target, weapon),
                            kill_probability=weapon.kill_probability
                        )
            
            if best_allocation:
                allocations.append(best_allocation)
                sensor_used[best_allocation.sensor_id] = True
                weapon_used[best_allocation.weapon_id] = True
        
        unassigned = [t.id for t in targets if t.id not in [a.target_id for a in allocations]]
        
        total_score = sum(a.priority_score for a in allocations)
        
        return SolveResult(
            status=SolveStatus.FEASIBLE if allocations else SolveStatus.PARTIAL,
            allocations=allocations,
            total_priority_score=total_score,
            unassigned_targets=unassigned,
            solve_time_sec=time.time() - start_time
        )
    
    def _calc_coverage(self, target: Target, sensor: Sensor) -> float:
        """Calculate coverage factor based on range and FOV."""
        if sensor.id not in target.range_to_sensors:
            return 0.0
        
        range_ratio = target.range_to_sensors[sensor.id] / sensor.range_km
        if range_ratio > 1.0:
            return 0.0
        
        # Coverage improves as target gets closer
        return 1.0 - range_ratio * 0.5  # 0.5 to 1.0 range
    
    def _estimate_intercept(self, target: Target, weapon: Weapon) -> float:
        """Estimate intercept time in seconds."""
        range_km = target.range_to_sensors.get(weapon.id, 50)  # Default 50km
        # Assume weapon speed ~3x target
        relative_speed_kts = weapon.max_target_speed_kts * 0.7 - target.velocity_kts
        if relative_speed_kts <= 0:
            return 300.0  # Can't catch
        
        # Convert to time: range in nm / speed in knots * 3600
        range_nm = range_km / 1.852  # km to nm
        time_sec = (range_nm / max(relative_speed_kts, 1)) * 3600
        return min(max(time_sec, 5), 300)  # 5 to 300 sec range


def solve_from_tracks(
    track_data: List[Dict],
    sensor_data: List[Dict],
    weapon_data: List[Dict],
    time_limit_sec: int = 30
) -> SolveResult:
    """
    Convenience function to solve from raw track/sensor/weapon data.
    
    Args:
        track_data: List of dicts with keys: id, priority, velocity, type, lat, lon, alt, range_to_sensors
        sensor_data: List of dicts with keys: id, range_km, mode, azimuth_fov, elevation_fov
        weapon_data: List of dicts with keys: id, range_km, kill_prob, max_speed, type
    
    Returns:
        SolveResult
    """
    targets = [
        Target(
            id=t['id'],
            priority=t.get('priority', 5),
            velocity_kts=t.get('velocity', 300),
            type=t.get('type', 'aircraft'),
            lat=t.get('lat', 0),
            lon=t.get('lon', 0),
            altitude_ft=t.get('altitude', 0),
            range_to_sensors=t.get('range_to_sensors', {})
        )
        for t in track_data
    ]
    
    sensors = [
        Sensor(
            id=s['id'],
            range_km=s.get('range_km', 100),
            mode=s.get('mode', 'track'),
            azimuth_fov_deg=s.get('azimuth_fov', 60),
            elevation_fov_deg=s.get('elevation_fov', 30)
        )
        for s in sensor_data
    ]
    
    weapons = [
        Weapon(
            id=w['id'],
            range_km=w.get('range_km', 80),
            kill_probability=w.get('kill_prob', 0.8),
            max_target_speed_kts=w.get('max_speed', 1200),
            type=w.get('type', 'aa_missile')
        )
        for w in weapon_data
    ]
    
    allocator = MilpAllocator(time_limit_sec=time_limit_sec)
    return allocator.solve(targets, sensors, weapons)


if __name__ == "__main__":
    # Simple test
    targets = [
        Target(1, 8.0, 300, "aircraft", 30, 120, 30000, {1: 80, 2: 120}),
        Target(2, 10.0, 500, "missile", 31, 121, 5000, {1: 100, 2: 150}),
    ]
    sensors = [
        Sensor(1, 150, "track", 60, 30),
        Sensor(2, 120, "search", 90, 45),
    ]
    weapons = [
        Weapon(1, 100, 0.8, 1200, "aa_missile"),
        Weapon(2, 80, 0.7, 900, "sam"),
    ]
    
    allocator = MilpAllocator(time_limit_sec=10, verbose=True)
    result = allocator.solve(targets, sensors, weapons)
    
    print(f"Status: {result.status.value}")
    print(f"Solve time: {result.solve_time_sec:.2f}s")
    print(f"Total score: {result.total_priority_score:.2f}")
    print(f"Allocations: {len(result.allocations)}")
    for alloc in result.allocations:
        print(f"  Target {alloc.target_id} -> Sensor {alloc.sensor_id} + Weapon {alloc.weapon_id} (score={alloc.priority_score:.2f})")
    if result.unassigned_targets:
        print(f"Unassigned: {result.unassigned_targets}")
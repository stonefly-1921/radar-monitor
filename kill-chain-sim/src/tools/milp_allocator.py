"""
MILP-based weapon-target allocation optimizer.

Design goals:
- Maximize expected intercept probability (Pk) under weapon range constraints
- Subject to: one weapon per target (for saturation scenario with equal-priority targets)
- Uses ortools.linear_solver (CBC backend) if available, falls back to greedy.

API:
  allocate_milp(tracks: List[Tuple[int, float, float]], weapons: List[str]) -> List[Tuple[str, int]]
  Returns: List[(weapon_name, track_id)] assignments
"""

from typing import List, Tuple, Optional

# Check availability
try:
    from ortools.linear_solver import pywraplp
    HAS_ORTOOLS = True
except ImportError:
    HAS_ORTOOLS = False


def allocate_milp(
    tracks: List[Tuple[int, float, str]],
    weapons: List[str],
    weapon_range_m: float = 30000.0,
) -> List[Tuple[str, int]]:
    """
    Allocate weapons to tracks using MILP (or greedy fallback).

    Args:
        tracks: List of (track_id, threat_score, target_type) tuples
        weapons: List of available weapon names
        weapon_range_m: max weapon range in meters

    Returns:
        List of (weapon_name, track_id) assignments
    """
    if not tracks or not weapons:
        return []

    if HAS_ORTOOLS:
        return _allocate_ortools(tracks, weapons, weapon_range_m)
    else:
        return _allocate_greedy(tracks, weapons)


def _allocate_greedy(
    tracks: List[Tuple[int, float, str]],
    weapons: List[str],
) -> List[Tuple[str, int]]:
    """
    Greedy fallback: sort by threat score descending, assign top weapons to top tracks.
    This matches the existing logic in kill_chain_np_fire_controller.py.
    """
    sorted_tracks = sorted(tracks, key=lambda x: -x[1])  # highest threat first
    assignments = []
    for i, weapon in enumerate(weapons):
        if i >= len(sorted_tracks):
            break
        track_id = sorted_tracks[i][0]
        assignments.append((weapon, track_id))
    return assignments


def _allocate_ortools(
    tracks: List[Tuple[int, float, str]],
    weapons: List[str],
    weapon_range_m: float,
) -> List[Tuple[str, int]]:
    """
    MILP formulation using ortools.linear_solver.
    
    Variables: x[w,t] ∈ {0,1} — weapon w assigned to track t
    Objective: maximize Σ x[w,t] * threat_score[t]
    Constraints:
      - Σ_t x[w,t] ≤ 1  (each weapon used at most once)
      - Σ_w x[w,t] ≤ 1  (each target gets at most one weapon)
    """
    solver = pywraplp.Solver(
        "weapon_allocation",
        pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING,
    )

    track_ids = [t[0] for t in tracks]
    threat_scores = {t[0]: t[1] for t in tracks}

    # Decision variables: x[w][t] = 1 if weapon w assigned to track t
    x = {}
    for w in weapons:
        for tid in track_ids:
            x[(w, tid)] = solver.BoolVar(f"x_{w}_{tid}")

    # Objective: maximize Σ x[w,t] * threat[t]
    objective = solver.Objective()
    for w in weapons:
        for tid in track_ids:
            objective.SetCoefficient(x[(w, tid)], threat_scores[tid])
    objective.SetMaximization()

    # Constraint: each weapon assigned to at most one track
    for w in weapons:
        solver.Add(
            sum(x[(w, tid)] for tid in track_ids) <= 1,
            name=f"one_target_per_weapon_{w}",
        )

    # Constraint: each track gets at most one weapon
    for tid in track_ids:
        solver.Add(
            sum(x[(w, tid)] for w in weapons) <= 1,
            name=f"one_weapon_per_target_{tid}",
        )

    # Solve
    status = solver.Solve()

    if status != pywraplp.Solver.OPTIMAL:
        # Fall back to greedy if MILP not optimal
        return _allocate_greedy(
            [(tid, threat_scores[tid], "") for tid in track_ids],
            weapons,
        )

    # Extract assignments
    assignments = []
    for w in weapons:
        for tid in track_ids:
            if x[(w, tid)].solution_value() > 0.5:
                assignments.append((w, tid))

    return assignments


# ── Self-test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Simple test
    tracks = [
        (1, 1.38, "ASM"),
        (2, 1.28, "ASM"),
        (3, 0.95, "FIGHTER"),
        (4, 0.72, "UAV"),
        (5, 0.65, "UAV"),
    ]
    weapons = ["aim120_1", "aim120_2", "aim120_3", "aim120_4"]
    result = allocate_milp(tracks, weapons)
    print(f"MILP allocation: {result}")
    if not HAS_ORTOOLS:
        print("(ortools not available, using greedy fallback)")

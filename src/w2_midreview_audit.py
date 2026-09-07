"""
SupplyPrescript - Week 2 Mid-Review: Budget Constraint Audit
--------------------------------------------------------------------------
Verifies the optimizer's hard budget constraint is never violated.
Runs prescribe_batch() across multiple random batches (different
seeds) and multiple budget levels, then checks that total_cost never
exceeds the given budget in any run.

This is the evidence for the project's mid-review checkpoint:
"Prove that the SciPy/PuLP solver never recommends an action that
violates the hard budget constraints defined in the code."
"""

import sys
sys.path.insert(0, "src")

from w2_day3_json_output import prescribe_batch

SEEDS = [1, 2, 3, 4, 5]
BUDGETS = [300, 500, 800, 1200, 1500]


def run_audit():
    trials = []
    violations = 0

    for budget in BUDGETS:
        for seed in SEEDS:
            result = prescribe_batch(n_orders=200, budget=budget, seed=seed)
            summary = result["summary"]

            over_budget = summary["total_cost"] > summary["budget"]
            if over_budget:
                violations += 1

            trials.append({
                "budget": budget,
                "seed": seed,
                "total_cost": summary["total_cost"],
                "within_budget": not over_budget,
                "loss_reduction_pct": summary["loss_reduction_pct"],
            })

    return trials, violations


def main():
    trials, violations = run_audit()

    print(f"Ran {len(trials)} trials across {len(BUDGETS)} budget levels x {len(SEEDS)} seeds")
    print()
    print(f"{'Budget':>8} {'Seed':>5} {'Cost':>10} {'Within Budget':>15} {'Loss Reduction':>16}")
    for t in trials:
        print(
            f"{t['budget']:>8} {t['seed']:>5} {t['total_cost']:>10.2f} "
            f"{str(t['within_budget']):>15} {t['loss_reduction_pct']:>15.1f}%"
        )

    print()
    if violations == 0:
        print(f"AUDIT PASSED: 0 budget violations across {len(trials)} independent trials.")
    else:
        print(f"AUDIT FAILED: {violations} budget violations detected.")


if __name__ == "__main__":
    main()

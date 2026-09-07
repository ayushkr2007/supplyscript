# SupplyPrescript - Closed-Loop Prescriptive Analytics

Predicts supply chain shipment delays and prescribes optimal mitigation
actions (upgrade shipping, compensation voucher, or no action), then
closes the loop by comparing predicted vs. actual outcomes.

## Dataset
[DataCo Smart Supply Chain for Big Data Analysis](https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis)
(180,519 rows, 53 columns). Not committed to this repo due to size -
place `DataCoSupplyChainDataset.csv` in `data/` locally.

## Stack
- **Predictive:** XGBoost
- **Prescriptive:** PuLP (linear optimization)
- **Write-back:** FastAPI + SQLite (local dev stand-in for a
  production Snowflake write-back layer - same pattern, easier to
  run locally)
- **Dashboard:** React (Vite)

## Progress Log

### Week 1 - Predictive Baseline - Complete

**Day 1 - Data Loading & Audit**
Loaded dataset with `ISO-8859-1` encoding (180,519 rows x 53 cols).
Target `Late_delivery_risk` confirmed balanced (54.8% late / 45.2%
on-time). Identified columns to drop: `Product Description` (100%
null), `Order Zipcode` (86% null), plus 11 rows with trivial nulls.

**Day 2 - Exploratory Data Analysis**
Cleaned dataset (dropped cancelled shipments - never delivered, not a
valid delay case) to 172,754 rows. Found delay rate varies sharply by
`Shipping Mode` (40%-100%) but is fairly flat across region (57-60%)
and category (58-69%). Flagged that `Shipping Mode` and
`Days for shipment (scheduled)` are near-1:1 redundant in this
dataset.

**Day 3 - Feature Engineering**
Dropped leakage columns (`Days for shipping (real)`,
`Delivery Status`) and identifier columns (names, emails, zip codes).
Kept `Shipping Mode`, dropped the redundant `Days for shipment
(scheduled)`. Extracted date features (month, day-of-week, quarter,
weekend flag). Encoded 13 categorical columns. Produced an 80/20
stratified train/test split (35 features).

**Day 4 - Baseline XGBoost Model**
Trained baseline XGBoost classifier: **73.5% accuracy, F1 0.736,
ROC-AUC 0.826**. Feature importance showed `Shipping Mode` dominating
at ~70% - flagged for investigation as a potential leakage risk.

**Day 5 - Leakage Investigation**
Trained a second model excluding `Shipping Mode` to test whether its
dominance signaled leakage. Result: accuracy dropped to 63.6% and
ROC-AUC to 0.690 - confirming `Shipping Mode` is a legitimate,
order-time-known feature with genuine predictive value, not an
outcome proxy. Model A (with `Shipping Mode`) confirmed as primary.

**Day 6 - Hyperparameter Tuning**
Ran `RandomizedSearchCV` (30 candidates x 5-fold stratified CV,
scored on ROC-AUC) over depth, learning rate, subsampling, and
regularization params. Tuned model improved substantially over
baseline:

| Metric   | Baseline | Tuned  |
|----------|----------|--------|
| Accuracy | 73.5%    | 78.6%  |
| F1       | 0.736    | 0.800  |
| ROC-AUC  | 0.826    | 0.875  |

Best params: `max_depth=7`, `learning_rate=0.15`, `n_estimators=400`,
`subsample=1.0`, `colsample_bytree=0.6`, `min_child_weight=5`,
`gamma=0`. Final model saved as `models/xgb_tuned.pkl`.

**Day 7 - Week 1 Wrap-up**
Documented Week 1 progress. Predictive baseline complete and ready to
feed into Week 2's prescriptive optimization layer.

### Week 2 - Prescriptive Optimization & Dashboard - Complete

**Day 1 - Business Constraints & Optimizer Setup**
Designed a budget-constrained shipping-upgrade allocator using PuLP:
given a batch of high-risk orders and a fixed budget, decide which
orders to upgrade to minimize total expected loss. Grounded cost and
value-at-risk in real dataset columns (`Order Item Product Price`,
`Order Profit Per Order`) rather than invented figures. First run
with a generous budget upgraded 196/200 orders (not a binding
constraint); tightened the budget so the optimizer had to make real
trade-offs, cutting expected loss by 71.7% while upgrading only 84/200
orders.

**Day 2 - Multi-Option Prescription**
Expanded the binary upgrade/no-upgrade decision into 3 real
alternatives per order: **upgrade shipping** (8% of price, removes
delay risk), **compensation voucher** (flat $3 cost, mitigates 60% of
expected loss), and **no action**. Initial parameterization made the
voucher a dominated option (never selected); decoupled its cost from
order price so it competes on its own merits for higher-priced
orders. Result: 83.4% expected loss reduction under the same budget,
using a genuine mix of all three options.

**Day 3 - JSON Output & React Dashboard**
Refactored the optimizer into a single `prescribe_batch()` function
returning a clean JSON structure (summary + per-order records with
all three options' costs/outcomes). Built a React (Vite) dashboard
displaying the batch as a decision board: budget-deployed progress
bar, before/after expected loss, decision-count filters, and
per-order cards showing the full ledger of options considered.

**Mid-Project Review**
- *Optimization audit:* Ran the optimizer across 5 budget levels x 5
  seeds (25 independent trials) checking that `total_cost` never
  exceeds `budget`. First run found 7 apparent violations, all under
  $0.11 - traced to summing already-rounded per-order costs rather
  than the true unrounded totals used by the LP solver internally.
  Fixed by computing the summary total from unrounded costs. Re-ran:
  **0 violations across 25/25 trials.**
- *Write-back check:* Built a FastAPI backend (`src/api.py`) with a
  SQLite database. `POST /decisions` persists an executed
  prescription; `GET /decisions` lists execution history. Wired the
  dashboard's "Execute Decision" button to call this endpoint live,
  confirmed via manual testing that clicking it performs a real
  INSERT and the record round-trips correctly through the API.

**Day 5 - Dashboard Polish**
Added a "Recently Executed" panel (live from `GET /decisions`,
showing order, decision, cost, and time-since-execution, plus a
running spent total), offline detection (dashboard detects when the
backend is unreachable and shows a clear recovery message instead of
failing silently), and per-order error messages when execution fails.

### Week 3 - The Closed Loop (upcoming)
- Compare predicted cost/outcome vs. actual for executed decisions
  (using the `actual_outcome` / `actual_cost` fields already present
  in the decisions table)
- Build a "Decision ROI" feedback view tracking how often prescribed
  actions actually paid off

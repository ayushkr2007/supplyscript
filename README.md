# SupplyPrescript — Closed-Loop Prescriptive Analytics

Predicts supply chain shipment delays and prescribes optimal mitigation
actions (air freight, secondary supplier, delay launch), then closes
the loop by comparing predicted vs. actual outcomes.

## Dataset
[DataCo Smart Supply Chain for Big Data Analysis](https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis)
(180,519 rows, 53 columns). Not committed to this repo due to size —
place `DataCoSupplyChainDataset.csv` in `data/` locally.

## Stack
- **Predictive:** XGBoost
- **Prescriptive:** SciPy / PuLP (linear optimization) — Week 2
- **Write-back:** FastAPI + Snowflake — Week 3
- **Dashboard:** Retool / React — Week 2+

## Progress Log

### Week 1 — Predictive Baseline ✅ Complete

**Day 1 — Data Loading & Audit**
Loaded dataset with `ISO-8859-1` encoding (180,519 rows × 53 cols).
Target `Late_delivery_risk` confirmed balanced (54.8% late / 45.2%
on-time). Identified columns to drop: `Product Description` (100%
null), `Order Zipcode` (86% null), plus 11 rows with trivial nulls.

**Day 2 — Exploratory Data Analysis**
Cleaned dataset (dropped cancelled shipments — never delivered, not a
valid delay case) to 172,754 rows. Found delay rate varies sharply by
`Shipping Mode` (40%–100%) but is fairly flat across region (57–60%)
and category (58–69%). Flagged that `Shipping Mode` and
`Days for shipment (scheduled)` are near-1:1 redundant in this
dataset.

**Day 3 — Feature Engineering**
Dropped leakage columns (`Days for shipping (real)`,
`Delivery Status`) and identifier columns (names, emails, zip codes).
Kept `Shipping Mode`, dropped the redundant `Days for shipment
(scheduled)`. Extracted date features (month, day-of-week, quarter,
weekend flag). Encoded 13 categorical columns. Produced an 80/20
stratified train/test split (35 features).

**Day 4 — Baseline XGBoost Model**
Trained baseline XGBoost classifier: **73.5% accuracy, F1 0.736,
ROC-AUC 0.826**. Feature importance showed `Shipping Mode` dominating
at ~70% — flagged for investigation as a potential leakage risk.

**Day 5 — Leakage Investigation**
Trained a second model excluding `Shipping Mode` to test whether its
dominance signaled leakage. Result: accuracy dropped to 63.6% and
ROC-AUC to 0.690 — confirming `Shipping Mode` is a legitimate,
order-time-known feature with genuine predictive value, not an
outcome proxy. Model A (with `Shipping Mode`) confirmed as primary.

**Day 6 — Hyperparameter Tuning**
Ran `RandomizedSearchCV` (30 candidates × 5-fold stratified CV,
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

**Day 7 — Week 1 Wrap-up**
Documented Week 1 progress (this update). Predictive baseline is
complete and ready to feed into Week 2's prescriptive optimization
layer, which will take the model's delay predictions and recommend
mitigation actions (air freight / secondary supplier / delay launch)
subject to budget and time constraints.

### Week 2 — Prescriptive Solver (upcoming)
- Define business constraints (budget, time, capacity)
- Build SciPy/PuLP linear optimization for the 3 alternative actions
- Prescriptive UI cards showing trade-offs (cost vs. speed)

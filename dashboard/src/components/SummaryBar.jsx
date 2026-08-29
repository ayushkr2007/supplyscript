export default function SummaryBar({ summary }) {
  const budgetUsedPct = (summary.total_cost / summary.budget) * 100

  return (
    <section className="summary-bar" aria-label="Batch summary">
      <div className="summary-stat">
        <p className="summary-stat__label">Budget deployed</p>
        <p className="summary-stat__value">
          ${summary.total_cost.toFixed(2)}
          <span className="summary-stat__of">/ ${summary.budget.toFixed(2)}</span>
        </p>
        <div className="budget-track">
          <div className="budget-track__fill" style={{ width: `${Math.min(budgetUsedPct, 100)}%` }} />
        </div>
      </div>

      <div className="summary-stat">
        <p className="summary-stat__label">Expected loss, before &rarr; after</p>
        <p className="summary-stat__value">
          <span className="summary-stat__before">${summary.expected_loss_before.toFixed(0)}</span>
          <span className="summary-stat__arrow">&rarr;</span>
          <span className="summary-stat__after">${summary.expected_loss_after.toFixed(0)}</span>
        </p>
        <p className="summary-stat__delta">&minus;{summary.loss_reduction_pct}% risk exposure</p>
      </div>

      <div className="summary-stat">
        <p className="summary-stat__label">Decisions issued</p>
        <p className="summary-stat__value summary-stat__value--mono">{summary.batch_size}</p>
        <p className="summary-stat__delta">
          {summary.decision_counts.upgrade} upgraded &middot; {summary.decision_counts.discount} offered vouchers &middot; {summary.decision_counts.nothing} held
        </p>
      </div>
    </section>
  )
}

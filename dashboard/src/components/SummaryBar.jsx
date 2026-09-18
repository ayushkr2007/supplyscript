export default function SummaryBar({ summary }) {
  const budgetUsedPct = (summary.total_cost / summary.budget) * 100

  return (
<<<<<<< HEAD
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
=======
    <section className="ticker" aria-label="Batch summary">
      <div className="ticker-item">
        <span className="ticker-item__label">Budget</span>
        <span className="ticker-item__value mono">
          ${summary.total_cost.toFixed(2)} <span className="ticker-item__of">/ ${summary.budget.toFixed(2)}</span>
        </span>
        <div className="ticker-item__bar">
          <div className="ticker-item__bar-fill" style={{ width: `${Math.min(budgetUsedPct, 100)}%` }} />
        </div>
      </div>

      <div className="ticker-divider" aria-hidden="true" />

      <div className="ticker-item">
        <span className="ticker-item__label">Expected loss</span>
        <span className="ticker-item__value mono">
          <span className="ticker-item__before">${summary.expected_loss_before.toFixed(0)}</span>
          <span className="ticker-item__arrow">&rarr;</span>
          <span className="ticker-item__after">${summary.expected_loss_after.toFixed(0)}</span>
        </span>
        <span className="ticker-item__delta ticker-item__delta--down mono">&minus;{summary.loss_reduction_pct}%</span>
      </div>

      <div className="ticker-divider" aria-hidden="true" />

      <div className="ticker-item">
        <span className="ticker-item__label">Decisions</span>
        <span className="ticker-item__value mono">{summary.batch_size}</span>
        <span className="ticker-item__delta mono">
          {summary.decision_counts.upgrade}U &middot; {summary.decision_counts.discount}V &middot; {summary.decision_counts.nothing}H
        </span>
>>>>>>> 5ddb4539a26d9c38b2698aec25820bd8b87b0fac
      </div>
    </section>
  )
}

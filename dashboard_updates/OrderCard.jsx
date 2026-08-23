const OPTION_META = {
  upgrade: { label: 'Upgrade', tone: 'upgrade' },
  discount: { label: 'Voucher', tone: 'discount' },
  nothing: { label: 'Hold', tone: 'nothing' },
}

export default function OrderCard({ order, executionStatus, onExecute }) {
  const riskPct = Math.round(order.risk_score * 100)
  const status = executionStatus || 'idle'

  return (
    <article className="order-card">
      <div className="order-card__top">
        <span className="order-card__id">ORDER #{String(order.order_id).padStart(4, '0')}</span>
        <RiskGauge value={order.risk_score} />
      </div>

      <div className="order-card__risk-row">
        <span className="order-card__risk-pct">{riskPct}%</span>
        <span className="order-card__risk-label">delay risk</span>
        <span className="order-card__vaR">${order.value_at_risk.toFixed(2)} at risk</span>
      </div>

      <div className="ledger" role="group" aria-label="Options considered">
        {['upgrade', 'discount', 'nothing'].map((key) => {
          const opt = order.options[key]
          const meta = OPTION_META[key]
          const chosen = order.decision === key
          return (
            <div
              key={key}
              className={`ledger-row ${chosen ? `ledger-row--chosen ledger-row--${meta.tone}` : 'ledger-row--dim'}`}
            >
              <span className="ledger-row__marker">{chosen ? 'e' : 'o'}</span>
              <span className="ledger-row__label">{meta.label}</span>
              <span className="ledger-row__cost">${opt.cost.toFixed(2)}</span>
              <span className="ledger-row__loss">${opt.expected_loss_after.toFixed(2)} left</span>
            </div>
          )
        })}
      </div>

      <button
        className={`execute-btn execute-btn--${status}`}
        onClick={() => onExecute(order)}
        disabled={status === 'loading' || status === 'done'}
      >
        {status === 'idle' && 'Execute Decision'}
        {status === 'loading' && 'Executing...'}
        {status === 'done' && 'Executed'}
        {status === 'error' && 'Failed - retry'}
      </button>
    </article>
  )
}

function RiskGauge({ value }) {
  const angle = value * 180
  return (
    <div className="risk-gauge" aria-hidden="true">
      <svg viewBox="0 0 36 20" width="36" height="20">
        <path d="M 2 18 A 16 16 0 0 1 34 18" fill="none" stroke="var(--border)" strokeWidth="3" strokeLinecap="round" />
        <path
          d="M 2 18 A 16 16 0 0 1 34 18"
          fill="none"
          stroke={value > 0.66 ? 'var(--danger)' : value > 0.33 ? 'var(--amber)' : 'var(--teal)'}
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={`${(angle / 180) * 50.27} 50.27`}
        />
      </svg>
    </div>
  )
}

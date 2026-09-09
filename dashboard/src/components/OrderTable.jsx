const OPTION_META = {
  upgrade: { label: 'UPG', tone: 'upgrade' },
  discount: { label: 'VCH', tone: 'discount' },
  nothing: { label: 'HLD', tone: 'nothing' },
}

function riskTone(value) {
  if (value > 0.66) return 'danger'
  if (value > 0.33) return 'amber'
  return 'teal'
}

export default function OrderTable({ orders, executionStatus, executionError, onExecute }) {
  return (
    <div className="order-table-wrap">
      <table className="order-table">
        <thead>
          <tr>
            <th className="col-id">Order</th>
            <th className="col-risk">Risk</th>
            <th className="col-num">At risk</th>
            <th className="col-decision">Decision</th>
            <th className="col-num">Cost</th>
            <th className="col-num">Loss after</th>
            <th className="col-action"></th>
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <OrderRow
              key={order.order_id}
              order={order}
              status={executionStatus[order.order_id] || 'idle'}
              error={executionError[order.order_id]}
              onExecute={onExecute}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}

function OrderRow({ order, status, error, onExecute }) {
  const riskPct = Math.round(order.risk_score * 100)
  const tone = riskTone(order.risk_score)
  const meta = OPTION_META[order.decision]

  return (
    <tr className={`order-row order-row--${status}`}>
      <td className="col-id mono">#{String(order.order_id).padStart(4, '0')}</td>
      <td className="col-risk">
        <div className="risk-cell">
          <div className="risk-bar">
            <div className={`risk-bar__fill risk-bar__fill--${tone}`} style={{ width: `${riskPct}%` }} />
          </div>
          <span className={`mono risk-cell__pct risk-cell__pct--${tone}`}>{riskPct}%</span>
        </div>
      </td>
      <td className="col-num mono">${order.value_at_risk.toFixed(2)}</td>
      <td className="col-decision">
        <span className={`decision-chip decision-chip--${meta.tone}`}>{meta.label}</span>
      </td>
      <td className="col-num mono">${order.cost.toFixed(2)}</td>
      <td className="col-num mono">${order.expected_loss_after.toFixed(2)}</td>
      <td className="col-action">
        <button
          className={`row-execute row-execute--${status}`}
          onClick={() => onExecute(order)}
          disabled={status === 'loading' || status === 'done'}
          title={status === 'error' ? error : undefined}
        >
          {status === 'idle' && 'Execute'}
          {status === 'loading' && '...'}
          {status === 'done' && 'Done'}
          {status === 'error' && 'Retry'}
        </button>
      </td>
    </tr>
  )
}

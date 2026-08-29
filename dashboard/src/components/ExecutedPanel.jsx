const DECISION_LABELS = {
  upgrade: 'Upgrade',
  discount: 'Voucher',
  nothing: 'Hold',
}

function timeAgo(isoString) {
  const diffMs = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export default function ExecutedPanel({ decisions, apiOnline }) {
  const spent = decisions
    .filter((d) => d.decision !== 'nothing')
    .reduce((sum, d) => sum + d.cost, 0)

  if (!apiOnline) {
    return (
      <section className="executed-panel executed-panel--offline" aria-label="Execution history">
        <p className="executed-panel__title">Execution history unavailable</p>
        <p className="executed-panel__hint">
          Backend not reachable at <code>localhost:8000</code>. Start it with{' '}
          <code>python -m uvicorn src.api:app --reload --port 8000</code>, then reload this page.
        </p>
      </section>
    )
  }

  return (
    <section className="executed-panel" aria-label="Execution history">
      <div className="executed-panel__header">
        <p className="executed-panel__title">Recently executed</p>
        <p className="executed-panel__spent">${spent.toFixed(2)} spent so far</p>
      </div>

      {decisions.length === 0 ? (
        <p className="executed-panel__empty">No decisions executed yet &mdash; click "Execute Decision" on any order.</p>
      ) : (
        <ul className="executed-panel__list">
          {decisions.slice(0, 8).map((d) => (
            <li key={d.id} className="executed-panel__item">
              <span className="executed-panel__order">#{String(d.order_id).padStart(4, '0')}</span>
              <span className={`executed-panel__decision executed-panel__decision--${d.decision}`}>
                {DECISION_LABELS[d.decision]}
              </span>
              <span className="executed-panel__cost">${d.cost.toFixed(2)}</span>
              <span className="executed-panel__time">{timeAgo(d.executed_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

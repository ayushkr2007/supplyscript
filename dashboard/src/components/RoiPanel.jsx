import { useEffect, useState } from 'react'

const DECISION_LABELS = {
  upgrade: 'Upgrade shipping',
  discount: 'Compensation voucher',
  nothing: 'No action',
}

// A decision "paid off" if the money spent (or withheld) matched reality:
//   - upgrade/discount: paid off if the order really was going to be late
//   - nothing: paid off if the order really was on time
function didPayOff(d) {
  const acted = d.decision !== 'nothing'
  const wasLate = d.actual_outcome === 'late'
  return acted ? wasLate : !wasLate
}

export default function RoiPanel({ decisions }) {
  const [batchStats, setBatchStats] = useState(null)
  const [batchError, setBatchError] = useState(false)

  useEffect(() => {
    fetch('/week3_day2_full_batch_eval.json')
      .then((res) => {
        if (!res.ok) throw new Error('not found')
        return res.json()
      })
      .then(setBatchStats)
      .catch(() => setBatchError(true))
  }, [])

  const evaluated = decisions.filter((d) => d.actual_outcome != null)
  const paidOff = evaluated.filter(didPayOff)
  const wasted = evaluated.filter((d) => d.decision !== 'nothing' && d.actual_outcome === 'on_time')
  const missed = evaluated.filter((d) => d.decision === 'nothing' && d.actual_outcome === 'late')
  const liveWastedSpend = wasted.reduce((sum, d) => sum + (d.actual_cost ?? 0), 0)

  const byDecision = {}
  for (const d of evaluated) {
    byDecision[d.decision] ??= { total: 0, paidOff: 0 }
    byDecision[d.decision].total += 1
    if (didPayOff(d)) byDecision[d.decision].paidOff += 1
  }

  return (
    <section className="roi-panel" aria-label="Decision ROI">
      <div className="roi-panel__header">
        <p className="roi-panel__title">Decision ROI</p>
        <p className="roi-panel__subhead">
          Did the prescribed actions actually pay off, checked against real outcomes
        </p>
      </div>

      {/* At-scale: the full 200-order batch, from Week 3 Day 2's ground-truth eval */}
      {batchStats && (
        <div className="roi-panel__scale">
          <p className="roi-panel__scale-label">At scale ({batchStats.n_orders} orders, full batch)</p>
          <div className="roi-stats">
            <div className="roi-stat">
              <p className="roi-stat__label">Precision</p>
              <p className="roi-stat__value">{(batchStats.precision * 100).toFixed(1)}%</p>
              <p className="roi-stat__sub">of $ spent went to orders that were truly late</p>
            </div>
            <div className="roi-stat">
              <p className="roi-stat__label">Recall</p>
              <p className="roi-stat__value">{(batchStats.recall * 100).toFixed(1)}%</p>
              <p className="roi-stat__sub">of truly-late orders were flagged for action</p>
            </div>
            <div className="roi-stat">
              <p className="roi-stat__label">Wasted spend</p>
              <p className="roi-stat__value roi-stat__value--danger">${batchStats.wasted_spend.toFixed(2)}</p>
              <p className="roi-stat__sub">{batchStats.wasted_spend_pct}% of total spend on orders that were never late</p>
            </div>
            <div className="roi-stat">
              <p className="roi-stat__label">Missed value</p>
              <p className="roi-stat__value">${batchStats.missed_value.toFixed(2)}</p>
              <p className="roi-stat__sub">at risk among truly-late orders left untouched</p>
            </div>
          </div>
        </div>
      )}
      {batchError && (
        <p className="roi-panel__hint">
          Full-batch stats not found. Run <code>python src/w3_day2_full_batch_eval.py</code>, then copy{' '}
          <code>data/week3_day2_full_batch_eval.json</code> into <code>dashboard/public/</code>.
        </p>
      )}

      {/* Live: decisions actually executed via this dashboard and checked against outcome */}
      <div className="roi-panel__live">
        <p className="roi-panel__scale-label">Live executed decisions</p>
        {evaluated.length === 0 ? (
          <p className="roi-panel__hint">
            No executed decisions have been checked against real outcomes yet. Execute a few from the board above,
            then run <code>python src/w3_day1_evaluate.py</code> and reload.
          </p>
        ) : (
          <>
            <p className="roi-panel__headline">
              {paidOff.length}/{evaluated.length} executed decisions paid off
              {' '}({((paidOff.length / evaluated.length) * 100).toFixed(1)}%)
              {' \u00b7 '}${liveWastedSpend.toFixed(2)} wasted{' \u00b7 '}{missed.length} missed
            </p>
            <ul className="roi-panel__breakdown">
              {Object.entries(byDecision).map(([decision, stats]) => (
                <li key={decision} className="roi-breakdown-row">
                  <span className={`roi-breakdown-row__label roi-breakdown-row__label--${decision}`}>
                    {DECISION_LABELS[decision]}
                  </span>
                  <span className="roi-breakdown-row__count">{stats.paidOff}/{stats.total} paid off</span>
                  <div className="roi-breakdown-row__bar">
                    <div
                      className={`roi-breakdown-row__fill roi-breakdown-row__fill--${decision}`}
                      style={{ width: `${(stats.paidOff / stats.total) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      <p className="roi-panel__caveat">
        Retrospective check against historical ground truth, not a causal experiment &mdash; see{' '}
        <code>src/w3_day1_evaluate.py</code> for the full caveat.
      </p>
    </section>
  )
}

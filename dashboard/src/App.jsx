import { useEffect, useState, useMemo, useCallback } from 'react'
import SummaryBar from './components/SummaryBar.jsx'
import OrderCard from './components/OrderCard.jsx'
import ExecutedPanel from './components/ExecutedPanel.jsx'
import RoiPanel from './components/RoiPanel.jsx'
import { fetchDecisions, postDecision } from './api.js'
import './App.css'

const DECISION_LABELS = {
  upgrade: 'Upgrade shipping',
  discount: 'Compensation voucher',
  nothing: 'No action',
}

export default function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')
  const [executionStatus, setExecutionStatus] = useState({})
  const [executionError, setExecutionError] = useState({})
  const [executedDecisions, setExecutedDecisions] = useState([])
  const [apiOnline, setApiOnline] = useState(true)

  useEffect(() => {
    fetch('/prescriptions.json')
      .then((res) => {
        if (!res.ok) throw new Error('prescriptions.json not found')
        return res.json()
      })
      .then(setData)
      .catch((err) => setError(err.message))
  }, [])

  const refreshDecisions = useCallback(() => {
    fetchDecisions()
      .then((decisions) => {
        setExecutedDecisions(decisions)
        setApiOnline(true)
      })
      .catch(() => setApiOnline(false))
  }, [])

  useEffect(() => {
    refreshDecisions()
  }, [refreshDecisions])

  const orders = useMemo(() => {
    if (!data) return []
    const sorted = [...data.orders].sort((a, b) => b.risk_score - a.risk_score)
    if (filter === 'all') return sorted
    return sorted.filter((o) => o.decision === filter)
  }, [data, filter])

  async function handleExecute(order) {
    setExecutionStatus((prev) => ({ ...prev, [order.order_id]: 'loading' }))
    setExecutionError((prev) => ({ ...prev, [order.order_id]: null }))

    const payload = {
      order_id: order.order_id,
      decision: order.decision,
      cost: order.cost,
      expected_loss_before: order.expected_loss_before,
      expected_loss_after: order.expected_loss_after,
      risk_score: order.risk_score,
    }

    try {
      await postDecision(payload)
      setExecutionStatus((prev) => ({ ...prev, [order.order_id]: 'done' }))
      refreshDecisions()
    } catch (err) {
      const isNetworkError = err instanceof TypeError
      const message = isNetworkError
        ? 'Backend unreachable - is it running on port 8000?'
        : err.message
      setExecutionStatus((prev) => ({ ...prev, [order.order_id]: 'error' }))
      setExecutionError((prev) => ({ ...prev, [order.order_id]: message }))
      setApiOnline(!isNetworkError)
    }
  }

  if (error) {
    return (
      <div className="state-screen">
        <p className="state-eyebrow">Board offline</p>
        <h1>Couldn't load the manifest.</h1>
        <p className="state-body">
          Run <code>python src/w2_day3_json_output.py</code> to generate{' '}
          <code>data/prescriptions.json</code>, then copy it into{' '}
          <code>public/prescriptions.json</code> here.
        </p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="state-screen">
        <p className="state-eyebrow">Loading</p>
        <h1>Pulling today's manifest&hellip;</h1>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <p className="eyebrow">SupplyPrescript &middot; Decision Board</p>
          <h1>Today's shipment manifest</h1>
          <p className="subhead">
            {data.summary.batch_size} orders scored &middot; budget allocated across the batch to minimize expected loss
          </p>
        </div>
      </header>

      <SummaryBar summary={data.summary} />

      <ExecutedPanel decisions={executedDecisions} apiOnline={apiOnline} />

      {apiOnline && <RoiPanel decisions={executedDecisions} />}

      <nav className="filter-row" aria-label="Filter by decision">
        <FilterPill label="All orders" active={filter === 'all'} onClick={() => setFilter('all')} count={data.summary.batch_size} />
        {Object.entries(data.summary.decision_counts).map(([key, count]) => (
          <FilterPill
            key={key}
            label={DECISION_LABELS[key]}
            active={filter === key}
            onClick={() => setFilter(key)}
            count={count}
            tone={key}
          />
        ))}
      </nav>

      <main className="order-grid">
        {orders.map((order) => (
          <OrderCard
            key={order.order_id}
            order={order}
            executionStatus={executionStatus[order.order_id]}
            executionError={executionError[order.order_id]}
            onExecute={handleExecute}
          />
        ))}
      </main>
    </div>
  )
}

function FilterPill({ label, active, onClick, count, tone }) {
  return (
    <button
      className={`filter-pill ${active ? 'filter-pill--active' : ''} ${tone ? `filter-pill--${tone}` : ''}`}
      onClick={onClick}
    >
      {label}
      <span className="filter-pill__count">{count}</span>
    </button>
  )
}

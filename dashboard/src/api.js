const API_BASE = 'http://localhost:8000'

export async function fetchDecisions() {
  const res = await fetch(`${API_BASE}/decisions`)
  if (!res.ok) throw new Error(`API returned ${res.status}`)
  return res.json()
}

export async function postDecision(payload) {
  const res = await fetch(`${API_BASE}/decisions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`API returned ${res.status}`)
  return res.json()
}

export { API_BASE }

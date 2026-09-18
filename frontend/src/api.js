async function get(path) {
  const res = await fetch(path)
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail || detail } catch {}
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  search: (q) => get(`/api/search?q=${encodeURIComponent(q)}`),
  quote: (s) => get(`/api/quote/${encodeURIComponent(s)}`),
  history: (s, period, interval) =>
    get(`/api/history/${encodeURIComponent(s)}?period=${period}&interval=${interval}`),
  forecast: (s) => get(`/api/forecast/${encodeURIComponent(s)}`),
  predictions: (s) => get(`/api/predictions/${encodeURIComponent(s)}`),
  news: (s) => get(`/api/news/${encodeURIComponent(s)}`),
  alerts: (s) => get(`/api/alerts/${encodeURIComponent(s)}`),
  context: (s) => get(`/api/context/${encodeURIComponent(s)}`),
  options: (s, expiry) =>
    get(`/api/options/${encodeURIComponent(s)}${expiry ? `?expiry=${encodeURIComponent(expiry)}` : ''}`),
  payoff: (s, strategy, expiry) =>
    get(`/api/payoff/${encodeURIComponent(s)}?strategy=${encodeURIComponent(strategy)}${expiry ? `&expiry=${encodeURIComponent(expiry)}` : ''}`),
  universes: () => get('/api/universes'),
  scanner: (u) => get(`/api/scanner?u=${encodeURIComponent(u)}`),
  watchlist: (symbols) => get(`/api/watchlist?symbols=${encodeURIComponent(symbols.join(','))}`),
}

export const fmtNum = (v, d = 2) =>
  v == null || Number.isNaN(v) ? '—' : Number(v).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d })

export const fmtCompact = (v) => {
  if (v == null) return '—'
  const abs = Math.abs(v)
  if (abs >= 1e12) return (v / 1e12).toFixed(2) + 'T'
  if (abs >= 1e9) return (v / 1e9).toFixed(2) + 'B'
  if (abs >= 1e6) return (v / 1e6).toFixed(2) + 'M'
  if (abs >= 1e3) return (v / 1e3).toFixed(1) + 'K'
  return v.toFixed(0)
}

export const fmtPct = (v, d = 2) => (v == null ? '—' : `${v > 0 ? '+' : ''}${v.toFixed(d)}%`)

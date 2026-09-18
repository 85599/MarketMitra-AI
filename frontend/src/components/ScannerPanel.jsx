import { useEffect, useState } from 'react'
import { api, fmtNum, fmtPct } from '../api'

const LS_KEY = 'mm_watchlist'

function tileColor(chg) {
  if (chg == null) return 'var(--panel-2)'
  const t = Math.min(Math.abs(chg) / 3, 1)
  return chg >= 0
    ? `rgba(34,197,94,${0.12 + t * 0.55})`
    : `rgba(239,68,68,${0.12 + t * 0.55})`
}

export default function ScannerPanel({ onPick }) {
  const [universes, setUniverses] = useState(null)
  const [uni, setUni] = useState('nifty50')
  const [scan, setScan] = useState(null)
  const [loading, setLoading] = useState(true)
  const [wl, setWl] = useState(() => {
    try { return JSON.parse(localStorage.getItem(LS_KEY) || '[]') } catch { return [] }
  })
  const [wlData, setWlData] = useState(null)
  const [input, setInput] = useState('')

  useEffect(() => {
    api.universes().then((d) => { setUniverses(d.universes); setUni(d.default) }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!uni) return
    let alive = true
    setLoading(true)
    api.scanner(uni)
      .then((d) => alive && setScan(d))
      .catch(() => alive && setScan(null))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [uni])

  useEffect(() => { localStorage.setItem(LS_KEY, JSON.stringify(wl)) }, [wl])

  useEffect(() => {
    if (!wl.length) { setWlData(null); return }
    let alive = true
    api.watchlist(wl).then((d) => alive && setWlData(d.symbols)).catch(() => {})
    return () => { alive = false }
  }, [wl])

  const addSymbol = () => {
    const s = input.trim().toUpperCase()
    if (s && !wl.includes(s)) setWl([...wl, s])
    setInput('')
  }

  const Movers = ({ rows, title, cls }) => (
    <div className="movers">
      <div className="section-label">{title}</div>
      {rows.map((r) => (
        <button key={r.symbol} className="mover" onClick={() => onPick(r.symbol)}>
          <span className="m-sym">{r.symbol}</span>
          <span className="m-name">{r.name}</span>
          <span className={`m-chg ${cls}`}>{fmtPct(r.changePercent)}</span>
        </button>
      ))}
    </div>
  )

  return (
    <div className="panel col-12">
      <div className="panel-head">
        <h2><span className="dot" />Market Scanner</h2>
        {universes && (
          <select className="select" value={uni} onChange={(e) => setUni(e.target.value)}>
            {universes.map((u) => <option key={u.id} value={u.id}>{u.label} · {u.count}</option>)}
          </select>
        )}
        {scan && <span className="badge gray">{scan.rows.length} names</span>}
      </div>

      {loading ? <div className="spinner" /> : !scan ? (
        <div className="empty">Scanner unavailable right now.</div>
      ) : (
        <div className="scanner-body">
          <div className="movers-row">
            <Movers rows={scan.gainers} title="Top gainers" cls="up" />
            <Movers rows={scan.losers} title="Top losers" cls="down" />
          </div>

          <div className="section-label" style={{ marginTop: 14 }}>Sector heatmap (avg % change)</div>
          <div className="sector-grid">
            {scan.sectors.map((s) => (
              <div key={s.sector} className="sector-tile" style={{ background: tileColor(s.changePercent) }}>
                <div className="s-name">{s.sector}</div>
                <div className={`s-chg ${s.changePercent >= 0 ? 'up' : 'down'}`}>{fmtPct(s.changePercent)}</div>
                <div className="s-count">{s.count} names</div>
              </div>
            ))}
          </div>

          <div className="section-label" style={{ marginTop: 14 }}>Heatmap (click to load)</div>
          <div className="heat-grid">
            {scan.rows.map((r) => (
              <button key={r.symbol} className="heat-tile" style={{ background: tileColor(r.changePercent) }} onClick={() => onPick(r.symbol)}>
                <span className="h-sym">{r.symbol.replace('.NS', '')}</span>
                <span className={`h-chg ${r.changePercent >= 0 ? 'up' : 'down'}`}>{fmtPct(r.changePercent, 1)}</span>
              </button>
            ))}
          </div>

          <div className="section-label" style={{ marginTop: 16 }}>Watchlist</div>
          <div className="wl-add">
            <input
              className="input"
              placeholder="Add symbol (e.g. INFY, AAPL, BTC-USD) + Enter"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') addSymbol() }}
            />
            <button className="btn" onClick={addSymbol}>Add</button>
          </div>
          {wl.length === 0 ? (
            <div className="empty" style={{ marginTop: 8 }}>No symbols yet — add any ticker to track it here.</div>
          ) : (
            <div className="table-wrap" style={{ marginTop: 8 }}>
              <table className="mini">
                <thead><tr><th>Symbol</th><th>Name</th><th>Price</th><th>Chg%</th><th>Class</th><th /></tr></thead>
                <tbody>
                  {(wlData ?? []).map((r) => (
                    <tr key={r.symbol}>
                      <td><button className="linkbtn" onClick={() => onPick(r.symbol)}>{r.symbol}</button></td>
                      <td className="dim">{r.name}</td>
                      <td>{fmtNum(r.price)}</td>
                      <td className={r.changePercent >= 0 ? 'up' : 'down'}>{fmtPct(r.changePercent)}</td>
                      <td><span className="badge blue">{r.classLabel}</span></td>
                      <td><button className="xbtn" onClick={() => setWl(wl.filter((s) => s !== r.symbol))}>✕</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

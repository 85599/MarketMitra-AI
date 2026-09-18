import { useEffect, useRef, useState } from 'react'
import { api, fmtNum, fmtCompact, fmtPct } from '../api'

// Pick the expiry closest to ~30 days out; near-dated (0DTE/weekly) chains are
// usually illiquid with zeroed OI/IV, so defaulting to them looks empty.
function pickDefaultExpiry(expiries) {
  if (!Array.isArray(expiries) || expiries.length === 0) return null
  const now = Date.now()
  let best = expiries[0]
  let bestDiff = Infinity
  for (const e of expiries) {
    const t = new Date(e + 'T00:00:00Z').getTime()
    if (Number.isNaN(t)) continue
    const diff = Math.abs(t - now - 30 * 864e5)
    if (diff < bestDiff) { bestDiff = diff; best = e }
  }
  return best
}

function IvSmile({ chain }) {
  const W = 340, H = 130, P = 22
  const rows = chain.filter((r) => (r.call?.iv != null && r.call.iv > 0) || (r.put?.iv != null && r.put.iv > 0))
  if (rows.length < 2) return <div className="empty">Not enough IV data across strikes for this expiry.</div>
  const strikes = rows.map((r) => r.strike)
  const lo = Math.min(...strikes), hi = Math.max(...strikes), span = hi - lo || 1
  const ivs = rows.flatMap((r) => [r.call?.iv, r.put?.iv].filter((v) => v != null && v > 0))
  const maxIv = Math.max(...ivs, 1)
  const X = (k) => P + ((k - lo) / span) * (W - 2 * P)
  const Y = (v) => H - P - (v / maxIv) * (H - 2 * P)
  const path = (get) => rows.map((r) => {
    const v = get(r)
    return v == null || v <= 0 ? null : `${X(r.strike).toFixed(1)},${Y(v).toFixed(1)}`
  }).filter(Boolean).join(' ')
  return (
    <div>
      <svg className="smile" viewBox={`0 0 ${W} ${H}`}>
        <line x1={P} y1={H - P} x2={W - P} y2={H - P} stroke="var(--border)" />
        <polyline points={path((r) => r.call?.iv)} fill="none" stroke="var(--up)" strokeWidth="2" />
        <polyline points={path((r) => r.put?.iv)} fill="none" stroke="var(--down)" strokeWidth="2" />
        {rows.map((r) => r.call?.iv > 0 && <circle key={'c' + r.strike} cx={X(r.strike)} cy={Y(r.call.iv)} r="2" fill="var(--up)" />)}
        {rows.map((r) => r.put?.iv > 0 && <circle key={'p' + r.strike} cx={X(r.strike)} cy={Y(r.put.iv)} r="2" fill="var(--down)" />)}
      </svg>
      <div className="legend">
        <span><i style={{ background: 'var(--up)' }} />Call IV</span>
        <span><i style={{ background: 'var(--down)' }} />Put IV</span>
        <span className="dim">peak {maxIv.toFixed(1)}%</span>
      </div>
    </div>
  )
}

function OiChange({ chain }) {
  const rows = chain.filter((r) => (r.call?.oiChange || r.put?.oiChange))
  if (!rows.length) return <div className="empty">No open-interest change data for this expiry (common off-market hours or for thin contracts).</div>
  const max = Math.max(...rows.flatMap((r) => [Math.abs(r.call?.oiChange || 0), Math.abs(r.put?.oiChange || 0)]), 1)
  const bar = (v, cls) => {
    const w = `${Math.min(100, (Math.abs(v) / max) * 100)}%`
    return <div className="oibar"><span className={cls} style={{ width: w }} /></div>
  }
  return (
    <div className="table-wrap" style={{ maxHeight: 300 }}>
      <table className="mini">
        <thead><tr><th>Call ΔOI</th><th style={{ textAlign: 'center' }}>Strike</th><th>Put ΔOI</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.strike} className={r.atm ? 'atm' : ''}>
              <td>{bar(r.call?.oiChange || 0, 'cbar')}{fmtCompact(r.call?.oiChange || 0)}</td>
              <td style={{ textAlign: 'center', fontWeight: 700 }}>{r.strike}</td>
              <td>{bar(r.put?.oiChange || 0, 'pbar')}{fmtCompact(r.put?.oiChange || 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function PayoffChart({ data }) {
  const W = 340, H = 160, P = 26
  const { spots, payoff, breakevens, spot } = data
  const lo = Math.min(...payoff), hi = Math.max(...payoff)
  const span = hi - lo || 1
  const xLo = Math.min(...spots), xHi = Math.max(...spots), xSpan = xHi - xLo || 1
  const X = (s) => P + ((s - xLo) / xSpan) * (W - 2 * P)
  const Y = (p) => H - P - ((p - lo) / span) * (H - 2 * P)
  const pts = spots.map((s, i) => `${X(s).toFixed(1)},${Y(payoff[i]).toFixed(1)}`).join(' ')
  const zeroY = Y(0)
  return (
    <div>
      <svg className="payoff" viewBox={`0 0 ${W} ${H}`}>
        <line x1={P} y1={zeroY} x2={W - P} y2={zeroY} stroke="var(--border)" strokeDasharray="4 3" />
        <polyline points={pts} fill="none" stroke="var(--accent)" strokeWidth="2" />
        {breakevens.map((b, i) => <circle key={i} cx={X(b)} cy={zeroY} r="3.5" fill="var(--text)" />)}
        {spot != null && spot >= xLo && spot <= xHi &&
          <line x1={X(spot)} y1={P} x2={X(spot)} y2={H - P} stroke="var(--text-dim)" strokeDasharray="2 3" />}
      </svg>
      <div className="legend">
        <span><i style={{ background: 'var(--accent)' }} />Payoff @ expiry</span>
        <span>○ breakeven</span>
        <span className="dim">┆ spot {fmtNum(spot)}</span>
      </div>
    </div>
  )
}

export default function OptionsPanel({ symbol }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [expiry, setExpiry] = useState(null)
  const didDefault = useRef(false)
  const [view, setView] = useState('chain')
  const [strategy, setStrategy] = useState('STRADDLE')
  const [payoff, setPayoff] = useState(null)
  const [payoffLoading, setPayoffLoading] = useState(false)

  useEffect(() => { setData(null); setExpiry(null); setPayoff(null); didDefault.current = false }, [symbol])

  useEffect(() => {
    let alive = true
    setLoading(true)
    api.options(symbol, expiry)
      .then((d) => {
        if (!alive) return
        setData(d)
        if (d?.available && expiry === null && !didDefault.current) {
          didDefault.current = true
          const preferred = pickDefaultExpiry(d.expiries)
          if (preferred && preferred !== d.expiry) setExpiry(preferred)
        }
      })
      .catch(() => alive && setData({ available: false }))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [symbol, expiry])

  const activeExpiry = expiry ?? data?.expiry
  useEffect(() => {
    if (!data?.available || !activeExpiry) return
    let alive = true
    setPayoffLoading(true)
    api.payoff(symbol, strategy, activeExpiry)
      .then((d) => alive && setPayoff(d))
      .catch(() => alive && setPayoff(null))
      .finally(() => alive && setPayoffLoading(false))
    return () => { alive = false }
  }, [symbol, strategy, activeExpiry, data?.available])

  const tabs = [['chain', 'Chain'], ['analytics', 'IV & OI'], ['payoff', 'Payoff']]

  return (
    <div className="panel col-6">
      <div className="panel-head">
        <h2><span className="dot" />Options Chain</h2>
        {data?.available && (
          <select className="select" value={activeExpiry} onChange={(e) => setExpiry(e.target.value)}>
            {data.expiries.slice(0, 14).map((e) => <option key={e} value={e}>{e}</option>)}
          </select>
        )}
        {data?.available && <span className="badge gray">spot {fmtNum(data.spot)}</span>}
      </div>

      {loading ? <div className="spinner" />
        : !data?.available ? (
          <div className="empty">
            Options chain unavailable for {symbol}. Chains work best on US-listed stocks & indices and
            Indian F&O names (NIFTY, BANKNIFTY, RELIANCE.NS, TCS.NS …).
          </div>
        ) : (
          <>
            <div className="seg small">
              {tabs.map(([id, label]) => (
                <button key={id} className={view === id ? 'active' : ''} onClick={() => setView(id)}>{label}</button>
              ))}
            </div>

            <div className="metric-grid" style={{ marginTop: 10, marginBottom: 12 }}>
              <div className="metric"><div className="label">PCR (OI)</div><div className="value">{data.stats?.pcr ?? '—'}</div></div>
              <div className="metric"><div className="label">Max pain</div><div className="value">{fmtNum(data.stats?.maxPain)}</div></div>
              <div className="metric"><div className="label">Call OI</div><div className="value">{fmtCompact(data.stats?.callOI)}</div></div>
              <div className="metric"><div className="label">Put OI</div><div className="value">{fmtCompact(data.stats?.putOI)}</div></div>
              <div className="metric"><div className="label">ATM IV</div><div className="value">{data.stats?.atmIV != null ? data.stats.atmIV + '%' : '—'}</div></div>
            </div>

            {view === 'chain' && (
              <div className="table-wrap" style={{ maxHeight: 320 }}>
                <table>
                  <thead>
                    <tr>
                      <th>Call OI</th><th>Call IV</th><th>Call LTP</th>
                      <th style={{ textAlign: 'center' }}>Strike</th>
                      <th>Put LTP</th><th>Put IV</th><th>Put OI</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.chain.map((row) => (
                      <tr key={row.strike} className={row.atm ? 'atm' : ''}>
                        <td>{row.call ? fmtCompact(row.call.oi) : '—'}</td>
                        <td>{row.call?.iv != null ? row.call.iv + '%' : '—'}</td>
                        <td className="up">{row.call ? fmtNum(row.call.ltp) : '—'}</td>
                        <td style={{ textAlign: 'center', fontWeight: 700 }}>{row.strike}</td>
                        <td className="down">{row.put ? fmtNum(row.put.ltp) : '—'}</td>
                        <td>{row.put?.iv != null ? row.put.iv + '%' : '—'}</td>
                        <td>{row.put ? fmtCompact(row.put.oi) : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {view === 'analytics' && (
              <div className="analytics">
                <div className="section-label">IV smile (per strike)</div>
                <IvSmile chain={data.chain} />
                <div className="section-label" style={{ marginTop: 14 }}>Open-interest change</div>
                <OiChange chain={data.chain} />
              </div>
            )}

            {view === 'payoff' && (
              <div className="payoff-wrap">
                <div className="row-between">
                  <select className="select" value={strategy} onChange={(e) => setStrategy(e.target.value)}>
                    {(payoff?.strategies ?? [{ id: 'STRADDLE', label: 'Long Straddle' }, { id: 'STRANGLE', label: 'Long Strangle' }, { id: 'BULL_CALL', label: 'Bull Call Spread' }, { id: 'BEAR_PUT', label: 'Bear Put Spread' }, { id: 'IRONCONDOR', label: 'Iron Condor' }])
                      .map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
                  </select>
                  {payoff?.netPremium != null && (
                    <span className={`badge ${payoff.netPremium > 0 ? 'red' : 'green'}`}>
                      {payoff.netPremium > 0 ? 'Net debit' : 'Net credit'} {fmtNum(Math.abs(payoff.netPremium))}
                    </span>
                  )}
                </div>
                {payoffLoading ? <div className="spinner" />
                  : !payoff ? <div className="empty">Payoff unavailable for this symbol/expiry.</div>
                  : (
                    <>
                      <PayoffChart data={payoff} />
                      <div className="metric-grid" style={{ marginTop: 10 }}>
                        <div className="metric"><div className="label">Max profit</div><div className="value up">{fmtNum(payoff.maxProfit)}</div></div>
                        <div className="metric"><div className="label">Max loss</div><div className="value down">{fmtNum(payoff.maxLoss)}</div></div>
                        <div className="metric"><div className="label">Breakevens</div><div className="value" style={{ fontSize: 13 }}>{payoff.breakevens.join(' / ') || '—'}</div></div>
                      </div>
                      <div className="legs">
                        {payoff.legs.map((l, i) => (
                          <span key={i} className={`leg ${l.side}`}>
                            {l.side === 'long' ? '▲' : '▼'} {l.type} {l.strike} · {fmtNum(l.premium)}
                          </span>
                        ))}
                      </div>
                      <div className="disclaimer">Per one unit of each leg, intrinsic value at expiry. Ignores lot size, margin and transaction costs.</div>
                    </>
                  )}
              </div>
            )}
          </>
        )}
    </div>
  )
}

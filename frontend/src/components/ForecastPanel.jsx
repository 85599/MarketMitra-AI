import { fmtNum, fmtPct } from '../api'

function HorizonChart({ lastClose, horizons }) {
  const W = 320, H = 90, P = 8
  const pts = [{ d: 0, p: lastClose }, ...horizons.map((h) => ({ d: h.h, p: h.predictedPrice }))]
  const maxD = pts[pts.length - 1].d || 1
  const vals = pts.map((x) => x.p)
  const lo = Math.min(...vals), hi = Math.max(...vals)
  const span = hi - lo || 1
  const X = (d) => P + (d / maxD) * (W - 2 * P)
  const Y = (p) => H - P - ((p - lo) / span) * (H - 2 * P)
  const line = pts.map((x) => `${X(x.d).toFixed(1)},${Y(x.p).toFixed(1)}`).join(' ')
  const area = `${P},${H - P} ${line} ${X(maxD).toFixed(1)},${H - P}`
  return (
    <svg className="hz-chart" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <polygon points={area} fill="var(--accent-soft)" />
      <polyline points={line} fill="none" stroke="var(--accent)" strokeWidth="2" />
      {pts.map((x, i) => (
        <circle key={i} cx={X(x.d)} cy={Y(x.p)} r="3" fill={i === 0 ? 'var(--text-dim)' : 'var(--accent)'} />
      ))}
    </svg>
  )
}

export default function ForecastPanel({ forecast, loading, error, onRetry }) {
  if (loading) return <div className="panel col-6"><div className="panel-head"><h2><span className="dot" />AI Forecast</h2></div><div className="spinner" /></div>
  if (error) return (
    <div className="panel col-6">
      <div className="panel-head"><h2><span className="dot" />AI Forecast</h2></div>
      <div className="error-box">{error}</div>
      <div style={{ marginTop: 12 }}><button className="btn" onClick={onRetry}>Retry</button></div>
    </div>
  )
  if (!forecast) return null

  const f = forecast
  const s = f.modelStats
  const up = f.direction === 'up'
  const [lo95, hi95] = f.range95
  const span = hi95 - lo95 || 1
  const pos = (v) => `${((v - lo95) / span) * 100}%`

  return (
    <div className="panel col-6">
      <div className="panel-head">
        <h2><span className="dot" />AI Forecast — Next Close</h2>
        <span className="badge blue">{s.architecture.split(' (')[0]}</span>
        <div className="spacer" />
        <button className="btn" onClick={onRetry}>↻ Re-run</button>
      </div>

      <div className="forecast-hero">
        <div>
          <div className={`forecast-price ${up ? 'up' : 'down'}`}>{fmtNum(f.predictedPrice)}</div>
          <div className="forecast-sub">
            {up ? '▲' : '▼'} {fmtPct(f.predictedReturn * 100)} vs last close {fmtNum(f.lastClose)}
          </div>
        </div>
        <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
          <div className="badge gray" style={{ fontSize: 11 }}>80% range</div>
          <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, marginTop: 4 }}>
            {fmtNum(f.range80[0])} – {fmtNum(f.range80[1])}
          </div>
        </div>
      </div>

      <div className="range-bar">
        <div className="range-track" />
        <div className="range-band80" style={{ left: pos(f.range80[0]), right: `calc(100% - ${pos(f.range80[1])})` }} />
        <div className="range-marker" style={{ left: pos(f.predictedPrice) }} />
      </div>
      <div className="range-labels">
        <span>{fmtNum(lo95)}</span>
        <span style={{ color: 'var(--text)' }}>95% band · predicted {fmtNum(f.predictedPrice)}</span>
        <span>{fmtNum(hi95)}</span>
      </div>

      <div className="metric-grid">
        <div className="metric"><div className="label">Direction acc.</div><div className="value">{(s.directionAccuracy * 100).toFixed(1)}%</div></div>
        <div className="metric"><div className="label">Backtest MAPE</div><div className="value">{s.mape.toFixed(2)}%</div></div>
        <div className="metric"><div className="label">Val. days</div><div className="value">{s.validationDays}</div></div>
        <div className="metric"><div className="label">Residual σ</div><div className="value">{(s.residualStd * 100).toFixed(2)}%</div></div>
      </div>

      {Array.isArray(f.horizons) && f.horizons.length > 1 && (
        <div className="hz-block">
          <div className="section-label">Multi-horizon path (1 / 5 / 10 day)</div>
          <HorizonChart lastClose={f.lastClose} horizons={f.horizons} />
          <div className="table-wrap">
            <table className="mini">
              <thead>
                <tr><th>Horizon</th><th>Pred. price</th><th>Return</th><th>80% range</th><th>Dir acc.</th><th>MAPE</th></tr>
              </thead>
              <tbody>
                {f.horizons.map((h) => (
                  <tr key={h.h}>
                    <td>{h.h}d</td>
                    <td className={h.direction === 'up' ? 'up' : 'down'}>{fmtNum(h.predictedPrice)}</td>
                    <td className={h.direction === 'up' ? 'up' : 'down'}>{fmtPct(h.predictedReturn * 100)}</td>
                    <td>{fmtNum(h.range80[0])} – {fmtNum(h.range80[1])}</td>
                    <td>{(h.directionAccuracy * 100).toFixed(0)}%</td>
                    <td>{h.mape.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="disclaimer">
        Model output is a probabilistic estimate from historical patterns — not investment advice.
        Ranges reflect backtest error; actual prices can fall outside them.
      </div>
    </div>
  )
}

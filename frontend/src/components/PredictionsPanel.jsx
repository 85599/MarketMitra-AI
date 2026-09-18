import { useState } from 'react'
import { fmtNum, fmtPct } from '../api'

export default function PredictionsPanel({ data, forecast, loading }) {
  const [tab, setTab] = useState('backtest') // backtest | saved

  if (loading) return <div className="panel col-6"><div className="panel-head"><h2><span className="dot" />Forecast vs Reality</h2></div><div className="spinner" /></div>
  if (!data && !forecast) return null

  const backtest = forecast?.history || []
  const saved = data?.predictions || []
  const perf = data?.performance || {}

  const hitRate = backtest.length
    ? backtest.filter((h) => Math.sign(h.predictedReturn) === Math.sign(h.actualReturn)).length / backtest.length
    : null

  return (
    <div className="panel col-6">
      <div className="panel-head">
        <h2><span className="dot" />Forecast vs Reality</h2>
        <div className="spacer" />
        <div className="seg">
          <button className={tab === 'backtest' ? 'active' : ''} onClick={() => setTab('backtest')}>Backtest</button>
          <button className={tab === 'saved' ? 'active' : ''} onClick={() => setTab('saved')}>Live Log ({saved.length})</button>
        </div>
      </div>

      {tab === 'backtest' ? (
        <>
          <div className="metric-grid" style={{ marginTop: 0, marginBottom: 12 }}>
            <div className="metric"><div className="label">Direction hit rate</div><div className="value">{hitRate == null ? '—' : (hitRate * 100).toFixed(1) + '%'}</div></div>
            <div className="metric"><div className="label">Days evaluated</div><div className="value">{backtest.length}</div></div>
            <div className="metric">
              <div className="label">Avg |error|</div>
              <div className="value">
                {backtest.length
                  ? (backtest.reduce((a, h) => a + Math.abs(h.predictedReturn - h.actualReturn), 0) / backtest.length * 100).toFixed(2) + '%'
                  : '—'}
              </div>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Pred. price</th><th>Actual</th><th>Pred. ret</th><th>Actual ret</th><th>Hit</th></tr></thead>
              <tbody>
                {backtest.slice().reverse().map((h) => {
                  const hit = Math.sign(h.predictedReturn) === Math.sign(h.actualReturn)
                  return (
                    <tr key={h.date}>
                      <td>{h.date}</td>
                      <td>{fmtNum(h.predictedPrice)}</td>
                      <td>{fmtNum(h.actualPrice)}</td>
                      <td className={h.predictedReturn >= 0 ? 'up' : 'down'}>{fmtPct(h.predictedReturn * 100)}</td>
                      <td className={h.actualReturn >= 0 ? 'up' : 'down'}>{fmtPct(h.actualReturn * 100)}</td>
                      <td>{hit ? <span className="badge green">✓</span> : <span className="badge red">✗</span>}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <>
          <div className="metric-grid" style={{ marginTop: 0, marginBottom: 12 }}>
            <div className="metric"><div className="label">Resolved</div><div className="value">{perf.resolved ?? 0}</div></div>
            <div className="metric"><div className="label">Direction acc.</div><div className="value">{perf.directionAccuracy == null ? '—' : (perf.directionAccuracy * 100).toFixed(1) + '%'}</div></div>
            <div className="metric"><div className="label">MAPE</div><div className="value">{perf.mape == null ? '—' : perf.mape.toFixed(2) + '%'}</div></div>
            <div className="metric"><div className="label">Inside 80% band</div><div className="value">{perf.within80Band == null ? '—' : (perf.within80Band * 100).toFixed(0) + '%'}</div></div>
          </div>
          {saved.length === 0 ? (
            <div className="empty">No live predictions logged yet — they appear here after visiting this symbol.</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Created</th><th>Target</th><th>Last close</th><th>Predicted</th><th>Actual</th><th>Error</th></tr></thead>
                <tbody>
                  {saved.map((p) => {
                    const err = p.actual_price != null
                      ? ((p.predicted_price - p.actual_price) / p.actual_price * 100)
                      : null
                    return (
                      <tr key={p.id}>
                        <td>{p.created_at.slice(5, 16)}</td>
                        <td>{p.target_date}</td>
                        <td>{fmtNum(p.last_close)}</td>
                        <td className={p.predicted_return >= 0 ? 'up' : 'down'}>{fmtNum(p.predicted_price)}</td>
                        <td>{p.actual_price != null ? fmtNum(p.actual_price) : <span className="badge gray">pending</span>}</td>
                        <td>{err == null ? '—' : <span className={Math.abs(err) < 1 ? 'up' : 'down'}>{fmtPct(err)}</span>}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}

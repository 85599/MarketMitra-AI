import { fmtPct } from '../api'

function RsRow({ name, rs }) {
  const periods = ['1m', '3m', '6m', '1y']
  const maxAbs = Math.max(
    1,
    ...periods.flatMap((p) => [Math.abs(rs[p]?.[0] ?? 0), Math.abs(rs[p]?.[1] ?? 0)]),
  )
  return (
    <div className="rs-row">
      <div className="rs-name">vs {name}</div>
      <div className="rs-bars">
        {periods.map((p) => {
          const [sym, bench] = rs[p] || [null, null]
          if (sym == null) return null
          const lead = sym - (bench ?? 0)
          return (
            <div className="rs-bar-line" key={p}>
              <span className="lbl">{p}</span>
              <div className="rs-bar-track">
                <div
                  className="rs-bar-fill"
                  style={{
                    width: `${Math.min(100, (Math.abs(lead) / maxAbs) * 100)}%`,
                    background: lead >= 0 ? 'var(--green)' : 'var(--red)',
                  }}
                />
              </div>
              <span className={`val ${lead >= 0 ? 'up' : 'down'}`}>{fmtPct(lead, 1)}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function ContextPanel({ data, loading }) {
  if (loading) return <div className="panel col-12"><div className="panel-head"><h2><span className="dot" />Market Context</h2></div><div className="spinner" /></div>
  if (!data) return null

  const benchEntries = Object.entries(data.benchmarks || {})

  return (
    <div className="panel col-12">
      <div className="panel-head">
        <h2><span className="dot" />Relative Strength & Market Context</h2>
        <div className="spacer" />
        {data.sharpeRatio != null && <span className="badge blue">Sharpe {data.sharpeRatio}</span>}
        {data.annualizedVolatility != null && <span className="badge gray">Vol {data.annualizedVolatility}%</span>}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 22 }}>
        <div>
          <div style={{ fontSize: 12, color: 'var(--text-dim)', fontWeight: 600, marginBottom: 2 }}>
            Position in 52-week range
          </div>
          <div className="pos-meter">
            <div className="knob" style={{ left: `${Math.max(0, Math.min(100, data.positionInRange52))}%` }} />
          </div>
          <div className="range-labels">
            <span>{data.low52}</span>
            <span>{data.positionInRange52.toFixed(0)}%</span>
            <span>{data.high52}</span>
          </div>

          <div style={{ marginTop: 18 }}>
            {benchEntries.map(([sym, b]) => (
              <div key={sym} style={{ display: 'flex', gap: 14, flexWrap: 'wrap', padding: '6px 0', fontSize: 12.5 }}>
                <span style={{ fontWeight: 600 }}>{b.name}</span>
                <span style={{ color: 'var(--text-dim)' }}>β {b.beta ?? '—'}</span>
                <span style={{ color: 'var(--text-dim)' }}>corr {b.correlation}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div style={{ fontSize: 12, color: 'var(--text-dim)', fontWeight: 600, marginBottom: 6 }}>
            Relative strength (stock return − benchmark return)
          </div>
          {benchEntries.length === 0 ? (
            <div className="empty">Benchmark data unavailable right now.</div>
          ) : (
            benchEntries.map(([sym, b]) => <RsRow key={sym} name={b.name} rs={b.rs} />)
          )}
        </div>
      </div>
    </div>
  )
}

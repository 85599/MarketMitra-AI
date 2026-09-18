const ICONS = {
  sharp_move: '⚡', rsi_overbought: '🔥', rsi_oversold: '❄️',
  macd_bullish_cross: '📈', macd_bearish_cross: '📉',
  golden_cross: '✨', golden_cross_50: '↑', death_cross: '💀', break_below_50: '↓',
  volume_spike: '📊', bb_breakout_up: '▲', bb_breakout_down: '▼',
  near_52w_high: '🏔', near_52w_low: '🕳',
}

export default function AlertsPanel({ data, loading }) {
  if (loading) return <div className="panel col-6"><div className="panel-head"><h2><span className="dot" />Market Alerts</h2></div><div className="spinner" /></div>

  const alerts = data?.alerts || []
  return (
    <div className="panel col-6">
      <div className="panel-head">
        <h2><span className="dot" />Market Alerts</h2>
        {alerts.length > 0
          ? <span className="badge amber">{alerts.length} active</span>
          : <span className="badge gray">monitoring</span>}
      </div>
      {alerts.length === 0 ? (
        <div className="empty">No alerts — nothing unusual in recent price action.</div>
      ) : (
        <div style={{ maxHeight: 380, overflowY: 'auto' }}>
          {alerts.map((a) => (
            <div key={a.id} className="alert-item">
              <div className={`alert-icon ${a.severity}`}>{ICONS[a.type] || '🔔'}</div>
              <div>
                <div className="alert-msg">{a.message}</div>
                <div className="alert-meta">
                  <span className="badge gray">{a.type.replace(/_/g, ' ')}</span> · {a.date} · severity: {a.severity}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

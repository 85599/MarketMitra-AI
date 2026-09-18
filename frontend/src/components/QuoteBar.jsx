import { fmtNum, fmtCompact, fmtPct } from '../api'

export default function QuoteBar({ quote, stats }) {
  if (!quote) return null
  const up = (quote.changePercent ?? 0) >= 0
  return (
    <div className="quote-bar">
      <div className="quote-title">
        <h1>
          {quote.name}
          <span className="ticker">{quote.symbol}</span>
          {quote.classLabel && <span className="badge blue">{quote.classLabel}</span>}
          {quote.sector && <span className="badge gray">{quote.sector}</span>}
        </h1>
        <div className="sub">
          {[quote.exchange, quote.industry, quote.currency].filter(Boolean).join(' · ')}
        </div>
      </div>
      <div className="quote-stats">
        <div className="stat"><div className="label">Open</div><div className="value">{fmtNum(quote.open)}</div></div>
        <div className="stat"><div className="label">Day Range</div><div className="value">{fmtNum(quote.dayLow)} – {fmtNum(quote.dayHigh)}</div></div>
        <div className="stat"><div className="label">52W Range</div><div className="value">{fmtNum(quote.week52Low)} – {fmtNum(quote.week52High)}</div></div>
        <div className="stat"><div className="label">Mkt Cap</div><div className="value">{fmtCompact(quote.marketCap)}</div></div>
        <div className="stat"><div className="label">P/E</div><div className="value">{fmtNum(quote.pe, 1)}</div></div>
        {stats?.volatilityAnn != null && (
          <div className="stat"><div className="label">Vol (ann.)</div><div className="value">{stats.volatilityAnn}%</div></div>
        )}
        {stats?.maxDrawdown != null && (
          <div className="stat"><div className="label">Max DD</div><div className="value down">{stats.maxDrawdown}%</div></div>
        )}
      </div>
      <div className="quote-price">
        <div className="price">{quote.currency === 'INR' ? '₹' : ''}{fmtNum(quote.price)}</div>
        <div className={`change ${up ? 'up' : 'down'}`}>
          {up ? '▲' : '▼'} {fmtNum(Math.abs(quote.change ?? 0))} ({fmtPct(quote.changePercent)})
        </div>
      </div>
    </div>
  )
}

import { useEffect, useRef, useState } from 'react'
import { api } from '../api'

const CLASSES = [
  { id: 'equity', label: 'Stocks', symbols: ['RELIANCE.NS', 'AAPL', 'TSLA', 'TCS.NS', 'INFY'] },
  { id: 'crypto', label: 'Crypto', symbols: ['BTC-USD', 'ETH-USD', 'ETH-INR', 'SOL-USD'] },
  { id: 'forex', label: 'Forex', symbols: ['USDINR=X', 'EURUSD=X', 'GBPINR=X'] },
  { id: 'commodity', label: 'Commodity', symbols: ['GC=F', 'SI=F', 'CL=F', 'NG=F'] },
  { id: 'index', label: 'Indices', symbols: ['^NSEI', '^GSPC', '^IXIC'] },
]

export default function SearchBar({ onSelect, initialSymbol }) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const [tab, setTab] = useState('equity')
  const timer = useRef(null)
  const wrapRef = useRef(null)

  useEffect(() => {
    const onClick = (e) => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current)
    if (q.trim().length < 1) { setResults([]); return }
    timer.current = setTimeout(async () => {
      try {
        const data = await api.search(q.trim())
        setResults(data.results || [])
        setActive(0)
        setOpen(true)
      } catch {
        setResults([])
      }
    }, 300)
    return () => timer.current && clearTimeout(timer.current)
  }, [q])

  const choose = (symbol) => {
    setOpen(false)
    setQ('')
    onSelect(symbol)
  }

  const onKey = (e) => {
    if (!open || results.length === 0) {
      if (e.key === 'Enter' && q.trim()) choose(q.trim().toUpperCase())
      return
    }
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(a + 1, results.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)) }
    else if (e.key === 'Enter') { e.preventDefault(); choose(results[active].symbol) }
    else if (e.key === 'Escape') setOpen(false)
  }

  return (
    <div style={{ display: 'contents' }}>
      <div className="search-wrap" ref={wrapRef}>
        <div className="search">
          <span className="icon">⌕</span>
          <input
            value={q}
            onChange={(e) => { setQ(e.target.value); setOpen(true) }}
            onKeyDown={onKey}
            placeholder={initialSymbol ? `Search stocks (current: ${initialSymbol})…` : 'Search stocks — try RELIANCE.NS, AAPL, TCS.NS…'}
          />
          {open && results.length > 0 && (
            <div className="search-results">
              {results.map((r, i) => (
                <button key={r.symbol} className={i === active ? 'active' : ''} onMouseEnter={() => setActive(i)} onClick={() => choose(r.symbol)}>
                  <span className="sym">{r.symbol}</span>
                  <span className="meta">{r.name}{r.exchange ? ` · ${r.exchange}` : ''}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="quick-chips">
        <div className="seg" style={{ marginRight: 4 }}>
          {CLASSES.map((c) => (
            <button key={c.id} className={tab === c.id ? 'active' : ''} onClick={() => setTab(c.id)}>{c.label}</button>
          ))}
        </div>
        {CLASSES.find((c) => c.id === tab).symbols.map((s) => (
          <button key={s} className="chip" onClick={() => choose(s)}>{s}</button>
        ))}
      </div>
    </div>
  )
}

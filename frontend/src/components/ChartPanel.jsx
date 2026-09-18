import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, LineStyle, CandlestickSeries, LineSeries, HistogramSeries } from 'lightweight-charts'

const MA_COLORS = { SMA20: '#f59e0b', SMA50: '#4f8cff', SMA200: '#a78bfa', EMA9: '#22d3ee' }

function makeChart(el, height) {
  return createChart(el, {
    height,
    layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#8b96ad', fontFamily: "'Inter', sans-serif", fontSize: 11 },
    grid: { vertLines: { color: 'rgba(31,42,68,.4)' }, horzLines: { color: 'rgba(31,42,68,.4)' } },
    rightPriceScale: { borderVisible: false },
    timeScale: { borderVisible: false, timeVisible: false },
    crosshair: {
      vertLine: { color: '#4f8cff', width: 1, style: LineStyle.Dashed, labelBackgroundColor: '#4f8cff' },
      horzLine: { color: '#4f8cff', width: 1, style: LineStyle.Dashed, labelBackgroundColor: '#4f8cff' },
    },
    autoSize: false,
  })
}

export default function ChartPanel({ data, symbol, period, setPeriod }) {
  const boxRef = useRef(null)
  const subRef = useRef(null)
  const chartRef = useRef(null)
  const subChartRef = useRef(null)
  const seriesRef = useRef({})
  const subSeriesRef = useRef([])
  const [overlays, setOverlays] = useState({ SMA20: true, SMA50: true, SMA200: false, EMA9: false, BB: false })
  const [subMode, setSubMode] = useState('volume') // volume | rsi | macd | returns

  // main chart lifecycle
  useEffect(() => {
    const el = boxRef.current
    if (!el) return
    const chart = makeChart(el, el.clientHeight)
    chartRef.current = chart
    const candle = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e', downColor: '#ef4444', wickUpColor: '#22c55e', wickDownColor: '#ef4444', borderVisible: false,
    })
    seriesRef.current.candle = candle
    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth, height: el.clientHeight }))
    ro.observe(el)
    return () => { ro.disconnect(); chart.remove() }
  }, [])

  // sub chart lifecycle
  useEffect(() => {
    const el = subRef.current
    if (!el) return
    const chart = makeChart(el, el.clientHeight)
    subChartRef.current = chart
    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth, height: el.clientHeight }))
    ro.observe(el)
    return () => { ro.disconnect(); chart.remove() }
  }, [])

  // feed candles
  useEffect(() => {
    const chart = chartRef.current
    if (!chart || !data) return
    seriesRef.current.candle.setData(data.candles)
    chart.timeScale().fitContent()
  }, [data])

  // overlays
  useEffect(() => {
    const chart = chartRef.current
    if (!chart || !data) return
    Object.values(seriesRef.current.lines || {}).forEach((s) => { try { chart.removeSeries(s) } catch {} })
    const lines = {}
    const byTime = {}
    data.indicators.forEach((row) => { byTime[row.time] = row })
    for (const key of ['SMA20', 'SMA50', 'SMA200', 'EMA9']) {
      if (!overlays[key]) continue
      const pts = data.indicators
        .filter((r) => r[key] != null)
        .map((r) => ({ time: r.time, value: r[key] }))
      lines[key] = chart.addSeries(LineSeries, { color: MA_COLORS[key], lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false })
      lines[key].setData(pts)
    }
    if (overlays.BB) {
      for (const key of ['BB_UPPER', 'BB_LOWER']) {
        const pts = data.indicators.filter((r) => r[key] != null).map((r) => ({ time: r.time, value: r[key] }))
        lines[key] = chart.addSeries(LineSeries, { color: 'rgba(148,163,184,.55)', lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false })
        lines[key].setData(pts)
      }
    }
    seriesRef.current.lines = lines
  }, [data, overlays])

  // sub chart content
  useEffect(() => {
    const chart = subChartRef.current
    if (!chart || !data) return
    chart.clearSeries?.()
    // clearSeries may not exist on all versions; remove series defensively
    const series = subSeriesRef.current
    series.forEach((s) => { try { chart.removeSeries(s) } catch {} })
    subSeriesRef.current = []
    const push = (s) => { subSeriesRef.current.push(s); return s }

    if (subMode === 'volume') {
      const vol = push(chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: '' }))
      vol.priceScale().applyOptions({ scaleMargins: { top: 0.75, bottom: 0 } })
      vol.setData(data.candles.map((c, i) => ({
        time: c.time, value: c.volume,
        color: c.close >= c.open ? 'rgba(34,197,94,.45)' : 'rgba(239,68,68,.45)',
      })))
    } else if (subMode === 'rsi') {
      const rsi = push(chart.addSeries(LineSeries, { color: '#a78bfa', lineWidth: 2, priceLineVisible: false }))
      rsi.setData(data.indicators.filter((r) => r.RSI14 != null).map((r) => ({ time: r.time, value: r.RSI14 })))
      for (const level of [30, 70]) {
        rsi.createPriceLine({ price: level, color: level === 70 ? '#ef4444' : '#22c55e', lineWidth: 1, lineStyle: LineStyle.Dotted, axisLabelVisible: true })
      }
    } else if (subMode === 'macd') {
      const macdPts = data.indicators.filter((r) => r.MACD != null)
      const macdLine = push(chart.addSeries(LineSeries, { color: '#4f8cff', lineWidth: 2, priceLineVisible: false, lastValueVisible: false }))
      macdLine.setData(macdPts.map((r) => ({ time: r.time, value: r.MACD })))
      const sig = push(chart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false }))
      sig.setData(macdPts.filter((r) => r.MACD_SIGNAL != null).map((r) => ({ time: r.time, value: r.MACD_SIGNAL })))
      const hist = push(chart.addSeries(HistogramSeries, { priceFormat: { type: 'price', precision: 4, minMove: 0.0001 }, priceLineVisible: false, lastValueVisible: false }))
      hist.setData(macdPts.filter((r) => r.MACD_HIST != null).map((r) => ({ time: r.time, value: r.MACD_HIST, color: r.MACD_HIST >= 0 ? 'rgba(34,197,94,.5)' : 'rgba(239,68,68,.5)' })))
    } else if (subMode === 'returns') {
      const rets = push(chart.addSeries(HistogramSeries, { priceFormat: { type: 'custom', formatter: (v) => v.toFixed(2) + '%' }, priceLineVisible: false }))
      rets.setData(data.dailyReturns.map((r) => ({ time: r.time, value: r.value, color: r.value >= 0 ? 'rgba(34,197,94,.6)' : 'rgba(239,68,68,.6)' })))
    }
    chart.timeScale().fitContent()
  }, [data, subMode])

  const toggle = (k) => setOverlays((o) => ({ ...o, [k]: !o[k] }))

  return (
    <div className="panel col-8">
      <div className="panel-head">
        <h2><span className="dot" />{symbol} · Price</h2>
        {setPeriod && (
          <div className="seg">
            {['1mo', '3mo', '6mo', '1y', '2y', '5y'].map((p) => (
              <button key={p} className={period === p ? 'active' : ''} onClick={() => setPeriod(p)}>{p}</button>
            ))}
          </div>
        )}
        <div className="toggle-row">
          {['SMA20', 'SMA50', 'SMA200', 'EMA9', 'BB'].map((k) => (
            <button key={k} data-c={k.toLowerCase()} className={`toggle ${overlays[k] ? 'on' : ''}`} onClick={() => toggle(k)}>
              {k === 'BB' ? 'Bollinger' : k}
            </button>
          ))}
        </div>
        <div className="spacer" />
        <div className="seg">
          {['volume', 'rsi', 'macd', 'returns'].map((m) => (
            <button key={m} className={subMode === m ? 'active' : ''} onClick={() => setSubMode(m)}>
              {m === 'volume' ? 'Vol' : m.toUpperCase()}
            </button>
          ))}
        </div>
      </div>
      <div className="chart-box" ref={boxRef} />
      <div className="sub-chart">
        <span className="tag">{subMode === 'volume' ? 'Volume' : subMode === 'rsi' ? 'RSI (14)' : subMode === 'macd' ? 'MACD (12,26,9)' : 'Daily Returns %'}</span>
        <div ref={subRef} style={{ height: '100%' }} />
      </div>
    </div>
  )
}

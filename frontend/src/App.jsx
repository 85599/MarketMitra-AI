import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'
import SearchBar from './components/SearchBar'
import QuoteBar from './components/QuoteBar'
import ChartPanel from './components/ChartPanel'
import ForecastPanel from './components/ForecastPanel'
import PredictionsPanel from './components/PredictionsPanel'
import NewsPanel from './components/NewsPanel'
import AlertsPanel from './components/AlertsPanel'
import OptionsPanel from './components/OptionsPanel'
import ContextPanel from './components/ContextPanel'
import ScannerPanel from './components/ScannerPanel'

const DEFAULT_SYMBOL = 'RELIANCE.NS'

export default function App() {
  const [symbol, setSymbol] = useState(DEFAULT_SYMBOL)
  const [period, setPeriod] = useState('1y')
  const [quote, setQuote] = useState(null)
  const [history, setHistory] = useState(null)
  const [forecast, setForecast] = useState(null)
  const [predictions, setPredictions] = useState(null)
  const [news, setNews] = useState(null)
  const [alerts, setAlerts] = useState(null)
  const [context, setContext] = useState(null)
  const [loading, setLoading] = useState({})
  const [errors, setErrors] = useState({})
  const symbolRef = useRef(symbol)
  symbolRef.current = symbol

  const load = useCallback(async (key, fn) => {
    setLoading((l) => ({ ...l, [key]: true }))
    setErrors((e) => ({ ...e, [key]: null }))
    try {
      return await fn()
    } catch (err) {
      setErrors((e) => ({ ...e, [key]: err.message }))
      return null
    } finally {
      setLoading((l) => ({ ...l, [key]: false }))
    }
  }, [])

  const guarded = (sym, setter) => async (res) => {
    if (symbolRef.current === sym) setter(res)
    return res
  }

  const loadSymbol = useCallback(async (sym) => {
    load('quote', () => api.quote(sym).then(guarded(sym, setQuote)))
    load('history', () => api.history(sym, '1y', '1d').then(guarded(sym, setHistory)))
    load('forecast', () => api.forecast(sym).then(guarded(sym, setForecast)))
    load('predictions', () => api.predictions(sym).then(guarded(sym, setPredictions)))
    load('news', () => api.news(sym).then(guarded(sym, setNews)))
    load('alerts', () => api.alerts(sym).then(guarded(sym, setAlerts)))
    load('context', () => api.context(sym).then(guarded(sym, setContext)))
  }, [load])

  useEffect(() => {
    setQuote(null); setHistory(null); setForecast(null)
    setPredictions(null); setNews(null); setAlerts(null); setContext(null)
    setPeriod('1y')
    loadSymbol(symbol)
  }, [symbol, loadSymbol])

  useEffect(() => {
    if (!history && !loading.history) return
    const sym = symbol
    load('history', () => api.history(sym, period, '1d').then(guarded(sym, setHistory)))
  }, [period]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const t = setInterval(() => {
      const sym = symbolRef.current
      api.quote(sym).then((q) => { if (symbolRef.current === sym) setQuote(q) }).catch(() => {})
    }, 30000)
    return () => clearInterval(t)
  }, [])

  const retryForecast = () => load('forecast', () => api.forecast(symbol).then(guarded(symbol, setForecast)))

  const anyLoading = loading.history && !history

  return (
    <div className="app">
      <header className="header">
        <div className="logo">
          <div className="logo-mark">📈</div>
          <div>
            MarketMitra AI
            <small>Multi-Asset Research Dashboard</small>
          </div>
        </div>
        <SearchBar onSelect={setSymbol} initialSymbol={symbol} />
      </header>

      {quote && <QuoteBar quote={quote} stats={history?.stats} />}

      {anyLoading ? (
        <div className="panel"><div className="spinner" /></div>
      ) : history ? (
        <div className="grid">
          <ChartPanel data={history} symbol={symbol} period={period} setPeriod={setPeriod} />
          <ForecastPanel forecast={forecast} loading={loading.forecast} error={errors.forecast} onRetry={retryForecast} />
          <PredictionsPanel data={predictions} forecast={forecast} loading={loading.predictions} />
          <NewsPanel data={news} loading={loading.news} />
          <AlertsPanel data={alerts} loading={loading.alerts} />
          <OptionsPanel symbol={symbol} />
          <ContextPanel data={context} loading={loading.context} />
          <ScannerPanel onPick={setSymbol} />
        </div>
      ) : (
        <div className="panel">
          <div className="error-box">
            {errors.history || `Could not load data for ${symbol}. Check the symbol (e.g. RELIANCE.NS, AAPL) and try again.`}
          </div>
        </div>
      )}

      <div className="footer">
        MarketMitra AI · Data from Yahoo Finance via yfinance · Forecasts are experimental model output, not investment advice.
      </div>
    </div>
  )
}

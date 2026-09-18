# MarketMitra AI

A full-stack **multi-asset** research dashboard: stocks, indices, crypto, forex,
commodities — plus a deep **options** view with chain, analytics and strategy
payoffs. Live market data, interactive charts with indicators, a multi-horizon
AI forecast with honest confidence ranges, prediction history with model
performance tracking, news sentiment, market alerts, relative-strength /
market-context analysis, and a market scanner with sector heatmap.

Indian underlyings are first-class: NSE/BSE equities and the **NIFTY / BANKNIFTY /
FINNIFTY** indices get a full options chain scraped from NSE India, while US-listed
names use Yahoo Finance options.


## Stack

| Layer     | Tech |
|-----------|------|
| Frontend  | React 18 + Vite, TradingView `lightweight-charts` v5, hand-rolled inline-SVG analytics, dark dashboard CSS |
| Backend   | Python FastAPI + uvicorn |
| Data      | `yfinance` (Yahoo Finance) + NSE India option-chain scraper, both TTL-cached |
| Forecast  | NumPy multi-output MLP ensemble (5 nets, 25-feature input, 3 horizons, Adam) trained per-request on 2y of daily data |
| Options   | Chain normalization, IV smile, OI change, max pain, PCR, and a pure-function strategy payoff builder |
| Storage   | SQLite (`backend/predictions.db`, path configurable via `MM_DB_PATH`) for the live prediction log |
| Quality   | pytest suite, ruff lint, Docker images, GitHub Actions CI |

## Features

- **Multi-asset** — asset-class tabs (Stocks / Crypto / Forex / Commodity / Indices) with quick symbols per class; class auto-detected from the symbol (`BTC-USD`, `USDINR=X`, `GC=F`, `^NSEI`, `RELIANCE.NS`…) and shown as a badge.
- **Search** any Yahoo symbol with debounced autocomplete.
- **Live quote bar** — price, change, day/52-week range, market cap, P/E, annualized vol, max drawdown. Polls every 30s.
- **Interactive chart** — candlesticks + volume, toggleable SMA20/50/200, EMA9, Bollinger bands; sub-pane switcher for Volume / RSI(14) / MACD(12,26,9) / daily returns; 1mo–5y ranges.
- **Multi-horizon AI Forecast** — a single multi-output MLP ensemble predicts **1-, 5- and 10-day-ahead** closes at once. Each horizon ships an 80% and 95% range derived from a 60-day walk-forward backtest (deliberately shown as a range, never a guaranteed number), plus per-horizon direction accuracy, MAPE and residual σ. A horizon chart plots the predicted price path.
- **Forecast vs Reality** — backtest table (predicted vs actual price/return per day with hit markers) and a **Live Log** of every forecast the app has made for the symbol, resolved against actual closes once they exist, with aggregate performance (direction accuracy, MAPE, % inside the 80% band).
- **Options — Chain** — expiry selector, ATM-windowed calls/puts table (LTP, IV, bid/ask, volume, OI, OI change) with the ATM strike highlighted, plus PCR (by OI), max pain, total call/put OI and ATM IV. Works for **Indian F&O names** (NIFTY, BANKNIFTY, FINNIFTY, `RELIANCE.NS`, `HDFCBANK.NS`, …) via NSE, and US-listed underlyings via Yahoo.
- **Options — IV & OI analytics** — inline-SVG **IV smile** (call vs put implied vol across strikes) and diverging **OI-change bars** per strike to spot where positioning is being added or unwound.
- **Options — Payoff builder** — pick a strategy (Long Straddle, Long Strangle, Bull Call Spread, Bear Put Spread, Iron Condor) and see the at-expiry **payoff diagram** with breakevens, net premium (debit/credit), max profit / max loss, and the leg ladder — all computed server-side by pure, unit-tested functions.
- **Market scanner** — batch-quoted universes (**Nifty 50**, S&P 500 leaders, major crypto) with top gainers/losers, a **sector heatmap** (average move per sector), and a clickable **symbol heatmap**; click any tile to load it. Plus a **watchlist** (persisted in `localStorage`) that mixes asset classes and shows live class-labeled quotes.
- **News sentiment** — Yahoo headlines scored with a finance lexicon (negation + intensifier aware), per-article pills and an overall gauge.
- **Market alerts** — sharp moves, RSI extremes, MACD crosses, golden/death crosses, 50-day MA breaks, volume spikes, Bollinger breaks, 52-week proximity.
- **Relative strength & context** — beta/correlation vs class-appropriate benchmarks (Nifty/S&P/Nasdaq for stocks; BTC/ETH for crypto; Dollar Index for forex & commodities), 1m/3m/6m/1y relative-strength bars, 52-week range position, Sharpe ratio.

## Run it locally

Prereqs: Python 3.10+, Node 18+.

```bash
# backend (port 8000)
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt   # macOS/Linux: .venv/bin/pip
.venv\Scripts\python -m uvicorn app.main:app --port 8000

# frontend (port 5173, proxies /api to :8000)
cd frontend
npm install
npm run dev
```

Or double-click `start.bat` (Windows) / run `./start.sh` (macOS/Linux) to launch both.

Open http://localhost:5173.

## Run it with Docker

Prereq: Docker + Docker Compose.

```bash
docker compose up --build
```

- Frontend → http://localhost:5173 (nginx serves the built SPA and proxies `/api` to the backend)
- Backend  → http://localhost:8000 (FastAPI; interactive docs at `/docs`)

The prediction log persists in the `backend-data` volume at `/app/data/predictions.db`.

## Tests & lint

```bash
cd backend
pip install -r requirements-dev.txt
pytest          # 58 tests: asset classes, indicators, alerts, payoff math,
                # forecast shape, and options/payoff HTTP endpoints (mocked chain)
ruff check .    # lint
```

The suite runs fully offline — synthetic OHLCV data and a mocked option chain, so
no network calls to Yahoo or NSE. CI (`.github/workflows/ci.yml`) runs ruff + pytest
for the backend and a production build for the frontend on every push/PR.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/search?q=` | Symbol autocomplete |
| `GET /api/quote/{sym}` | Live quote + asset class (30s cache) |
| `GET /api/history/{sym}?period=&interval=` | Candles + indicators + daily returns + stats |
| `GET /api/forecast/{sym}` | Train ensemble, predict 1/5/10-day closes + ranges + backtest; logs prediction |
| `GET /api/predictions/{sym}` | Saved prediction log + resolved performance |
| `GET /api/news/{sym}` | Headlines with sentiment scores |
| `GET /api/alerts/{sym}` | Rule-based alert list |
| `GET /api/options/{sym}?expiry=` | Options chain + PCR / max pain / IV / OI-change stats (NSE for Indian names) |
| `GET /api/payoff/{sym}?strategy=&expiry=` | Strategy legs, payoff curve, breakevens, max P/L, net premium |
| `GET /api/context/{sym}` | Beta/corr/RS vs class benchmarks, 52w position, Sharpe |
| `GET /api/universes` | Available scanner universes |
| `GET /api/scanner?u=` | Universe quotes → rows, gainers, losers, sector aggregates |
| `GET /api/watchlist?symbols=` | Live class-labeled quotes for a comma-separated list |

Strategies for `/api/payoff`: `STRADDLE`, `STRANGLE`, `BULL_CALL`, `BEAR_PUT`, `IRONCONDOR`.

## Notes

- Forecasts are experimental model output for research/education — not investment advice.
- Yahoo Finance is unofficial; respect their terms and rate limits. The backend caches quotes (30s), history (5m), news (10m), options (60s), scanner (2m) to stay polite.
- NSE option-chain data is scraped from public NSE India endpoints using a normal browser User-Agent with a cookie warm-up; NSE may rate-limit or change the schema. If a chain fails to load, the panel falls back to an empty state rather than erroring the whole page.

"""Curated scanner universes: symbol -> name + GICS-ish sector.

Sector is stored statically because fetching it per-symbol from Yahoo is slow
and rate-limited; these lists are the major index/crypto constituents.
"""

_NIFTY50 = [
    ("RELIANCE.NS", "Reliance Industries", "Energy"),
    ("ONGC.NS", "ONGC", "Energy"),
    ("COALINDIA.NS", "Coal India", "Energy"),
    ("NTPC.NS", "NTPC", "Utilities"),
    ("POWERGRID.NS", "Power Grid", "Utilities"),
    ("INFY.NS", "Infosys", "Information Technology"),
    ("TCS.NS", "Tata Consultancy Services", "Information Technology"),
    ("HCLTECH.NS", "HCLTech", "Information Technology"),
    ("WIPRO.NS", "Wipro", "Information Technology"),
    ("TECHM.NS", "Tech Mahindra", "Information Technology"),
    ("HDFCBANK.NS", "HDFC Bank", "Financials"),
    ("ICICIBANK.NS", "ICICI Bank", "Financials"),
    ("SBIN.NS", "State Bank of India", "Financials"),
    ("KOTAKBANK.NS", "Kotak Mahindra Bank", "Financials"),
    ("AXISBANK.NS", "Axis Bank", "Financials"),
    ("INDUSINDBK.NS", "IndusInd Bank", "Financials"),
    ("BAJFINANCE.NS", "Bajaj Finance", "Financials"),
    ("BAJAJFINSV.NS", "Bajaj Finserv", "Financials"),
    ("HDFCLIFE.NS", "HDFC Life", "Financials"),
    ("SBILIFE.NS", "SBI Life", "Financials"),
    ("MARUTI.NS", "Maruti Suzuki", "Consumer Discretionary"),
    ("TATAMOTORS.NS", "Tata Motors", "Consumer Discretionary"),
    ("M&M.NS", "Mahindra & Mahindra", "Consumer Discretionary"),
    ("BAJAJ-AUTO.NS", "Bajaj Auto", "Consumer Discretionary"),
    ("EICHERMOT.NS", "Eicher Motors", "Consumer Discretionary"),
    ("HEROMOTOCO.NS", "Hero MotoCorp", "Consumer Discretionary"),
    ("TITAN.NS", "Titan", "Consumer Discretionary"),
    ("NESTLEIND.NS", "Nestle India", "Consumer Staples"),
    ("HINDUNILVR.NS", "Hindustan Unilever", "Consumer Staples"),
    ("ITC.NS", "ITC", "Consumer Staples"),
    ("BRITANNIA.NS", "Britannia", "Consumer Staples"),
    ("ASIANPAINT.NS", "Asian Paints", "Materials"),
    ("TATASTEEL.NS", "Tata Steel", "Materials"),
    ("JSWSTEEL.NS", "JSW Steel", "Materials"),
    ("HINDALCO.NS", "Hindalco", "Materials"),
    ("ULTRACEMCO.NS", "UltraTech Cement", "Materials"),
    ("GRASIM.NS", "Grasim", "Materials"),
    ("CIPLA.NS", "Cipla", "Healthcare"),
    ("SUNPHARMA.NS", "Sun Pharma", "Healthcare"),
    ("DRREDDY.NS", "Dr Reddy's", "Healthcare"),
    ("DIVISLAB.NS", "Divi's Labs", "Healthcare"),
    ("APOLLOHOSP.NS", "Apollo Hospitals", "Healthcare"),
    ("LT.NS", "Larsen & Toubro", "Industrials"),
    ("ADANIPORTS.NS", "Adani Ports", "Industrials"),
    ("BEL.NS", "Bharat Electronics", "Industrials"),
    ("ADANIENT.NS", "Adani Enterprises", "Industrials"),
    ("BHARTIARTL.NS", "Bharti Airtel", "Communication Services"),
    ("DLF.NS", "DLF", "Real Estate"),
    ("TATACONSUM.NS", "Tata Consumer", "Consumer Staples"),
]

_SP500 = [
    ("AAPL", "Apple", "Information Technology"),
    ("MSFT", "Microsoft", "Information Technology"),
    ("NVDA", "NVIDIA", "Information Technology"),
    ("CRM", "Salesforce", "Information Technology"),
    ("ADBE", "Adobe", "Information Technology"),
    ("AMD", "AMD", "Information Technology"),
    ("INTC", "Intel", "Information Technology"),
    ("CSCO", "Cisco", "Information Technology"),
    ("ORCL", "Oracle", "Information Technology"),
    ("GOOGL", "Alphabet", "Communication Services"),
    ("META", "Meta", "Communication Services"),
    ("NFLX", "Netflix", "Communication Services"),
    ("DIS", "Disney", "Communication Services"),
    ("AMZN", "Amazon", "Consumer Discretionary"),
    ("TSLA", "Tesla", "Consumer Discretionary"),
    ("HD", "Home Depot", "Consumer Discretionary"),
    ("MCD", "McDonald's", "Consumer Discretionary"),
    ("NKE", "Nike", "Consumer Discretionary"),
    ("BRK-B", "Berkshire Hathaway", "Financials"),
    ("JPM", "JPMorgan", "Financials"),
    ("V", "Visa", "Financials"),
    ("MA", "Mastercard", "Financials"),
    ("UNH", "UnitedHealth", "Healthcare"),
    ("JNJ", "Johnson & Johnson", "Healthcare"),
    ("LLY", "Eli Lilly", "Healthcare"),
    ("PFE", "Pfizer", "Healthcare"),
    ("MRK", "Merck", "Healthcare"),
    ("ABT", "Abbott", "Healthcare"),
    ("TMO", "Thermo Fisher", "Healthcare"),
    ("XOM", "Exxon Mobil", "Energy"),
    ("CVX", "Chevron", "Energy"),
    ("PG", "Procter & Gamble", "Consumer Staples"),
    ("KO", "Coca-Cola", "Consumer Staples"),
    ("PEP", "PepsiCo", "Consumer Staples"),
    ("COST", "Costco", "Consumer Staples"),
    ("WMT", "Walmart", "Consumer Staples"),
    ("BA", "Boeing", "Industrials"),
    ("CAT", "Caterpillar", "Industrials"),
    ("HON", "Honeywell", "Industrials"),
    ("UPS", "UPS", "Industrials"),
    ("GE", "General Electric", "Industrials"),
    ("LIN", "Linde", "Materials"),
    ("FCX", "Freeport-McMoRan", "Materials"),
    ("NEE", "NextEra Energy", "Utilities"),
    ("DUK", "Duke Energy", "Utilities"),
]

_CRYPTO = [
    ("BTC-USD", "Bitcoin", "Crypto"),
    ("ETH-USD", "Ethereum", "Crypto"),
    ("SOL-USD", "Solana", "Crypto"),
    ("BNB-USD", "BNB", "Crypto"),
    ("XRP-USD", "XRP", "Crypto"),
    ("ADA-USD", "Cardano", "Crypto"),
    ("DOGE-USD", "Dogecoin", "Crypto"),
    ("AVAX-USD", "Avalanche", "Crypto"),
    ("DOT-USD", "Polkadot", "Crypto"),
    ("LINK-USD", "Chainlink", "Crypto"),
    ("TRX-USD", "TRON", "Crypto"),
    ("LTC-USD", "Litecoin", "Crypto"),
    ("SHIB-USD", "Shiba Inu", "Crypto"),
    ("TON-USD", "Toncoin", "Crypto"),
    ("MATIC-USD", "Polygon", "Crypto"),
]


def _pack(rows):
    return [{"symbol": s, "name": n, "sector": sec} for s, n, sec in rows]


UNIVERSES = {
    "nifty50": {"label": "Nifty 50 (India)", "symbols": _pack(_NIFTY50)},
    "sp500": {"label": "S&P 500 majors (US)", "symbols": _pack(_SP500)},
    "crypto": {"label": "Crypto (top coins)", "symbols": _pack(_CRYPTO)},
}

DEFAULT_UNIVERSE = "nifty50"


def get_universe(key: str):
    return UNIVERSES.get(key) or UNIVERSES[DEFAULT_UNIVERSE]

from fastapi import FastAPI
import requests, pandas as pd, time, os

app = FastAPI()

API_KEY = os.getenv("API_KEY")

sp500 = pd.read_csv("https://datahub.io/core/s-and-p-500-companies/r/constituents.csv")
symbols = sp500['Symbol'].tolist()

CACHE = {}
LAST_RUN = 0

def get_fundamentals(symbol):
    url = f"https://finnhub.io/api/v1/stock/metric?symbol={symbol}&metric=all&token={API_KEY}"
    return requests.get(url).json()

def score_stock(symbol):
    try:
        data = get_fundamentals(symbol)
        m = data.get("metric", {})

        pe = m.get("peBasicExclExtraTTM", 100)
        pb = m.get("pbAnnual", 10)
        debt = m.get("totalDebt/totalEquityAnnual", 1)
        roe = m.get("roeTTM", 0)
        growth = m.get("epsGrowth3Y", 0)
        eps = m.get("epsTTM", 1)

        intrinsic = eps * (8.5 + 2 * growth)
        price = m.get("currentEv/freeCashFlowTTM", intrinsic)

        margin = intrinsic - price

        score = (
            (15 - pe if pe < 15 else 0) +
            (1.5 - pb if pb < 1.5 else 0) +
            (0.5 - debt if debt < 0.5 else 0) +
            (roe / 10) +
            (margin / max(price,1))
        )

        return {"symbol": symbol, "score": score, "price": price, "intrinsic": intrinsic}
    except:
        return None

def get_top_stock():
    results = []
    for s in symbols[:100]:  # keep fast
        r = score_stock(s)
        if r:
            results.append(r)

    return sorted(results, key=lambda x: x["score"], reverse=True)[0]

@app.get("/top-stock")
def top_stock():
    global CACHE, LAST_RUN

    if time.time() - LAST_RUN < 3600:
        return CACHE

    CACHE = get_top_stock()
    LAST_RUN = time.time()

    return CACHE

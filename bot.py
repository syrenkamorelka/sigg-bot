import requests
import pandas as pd
import io
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1566471711510102102/vVBXiCEShPkZnQFD84U1PTUYOqm1qR3LeYvQu4YcYfBqI8ZcVo5uWlr2KG-UBjgXCH3B"
INITIAL_CAPITAL = 20000 
MAX_POSITION_PERCENT = 0.15  # Max 15% budżetu na jedną spółkę (~3000 zł)

# Lista ponad 100 spółek z GPW
TICKERS = [
    # WIG20
    "pko", "pkn", "pzu", "kgh", "peo", "ale", "cdr", "lpp", 
    "dnp", "spl", "alr", "mbk", "bdx", "kru", "kty", "pge", 
    "tpe", "pep", "jsw", "cps",
    # mWIG40
    "1at", "abs", "apr", "apt", "asb", "ase", "atc", "att",
    "ben", "bft", "bnp", "bos", "ccc", "cig", "cie", "cmr",
    "cvp", "dom", "eat", "ena", "epl", "eur", "grp", "gtc",
    "hug", "ing", "ker", "knt", "mil", "mob", "neu", "pco",
    "pcf", "pkp", "plw", "snt", "ten", "txt", "vrg", "wpp",
    "xtb", "zep",
    # sWIG80 i inne
    "acg", "act", "adv", "ago", "amb", "ams", "amr",
    "arh", "ast", "atd", "aot", "bow", "bhw", "cln", "cog",
    "cpg", "crm", "dat", "deb", "del", "dcr", "ent", "erb",
    "for", "fte", "gpw", "inc", "izo", "kgn", "lwb", "mci",
    "mgt", "mls", "moc", "mop", "nng", "oat", "opn", "pcr",
    "pka", "pnt", "pri", "rbw", "rig", "rob", "rvu", "san",
    "sel", "sfd", "shd", "sgp", "ska", "sth", "stp", "tor",
    "toa", "unt", "vox", "vot", "wwa",
    # ETF-y
    "etfbw20tr", "etfbm40tr"
]

def analyze_stock(symbol):
    try:
        url = f"https://stooq.pl/q/d/l/?s={symbol.lower()}.pl&i=d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)

        if response.status_code != 200 or len(response.text) < 50:
            return None

        df = pd.read_csv(io.StringIO(response.text))
        if df.empty or 'Zamkniecie' not in df.columns or len(df) < 30:
            return None

        df['Data'] = pd.to_datetime(df['Data'])
        df = df.sort_values('Data').reset_index(drop=True)

        close_prices = df["Zamkniecie"]
        rsi_int = RSIIndicator(close=close_prices, window=14)
        df["RSI"] = rsi_int.rsi()

        sma_short = SMAIndicator(close=close_prices, window=10)
        sma_long = SMAIndicator(close=close_prices, window=30)
        df["SMA10"] = sma_short.sma_indicator()
        df["SMA30"] = sma_long.sma_indicator()

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        current_price = round(float(latest["Zamkniecie"]), 2)
        rsi = round(float(latest["RSI"]), 2)

        signal = "HOLD"
        reason = "Brak silnego sygnału"

        if rsi < 35:
            signal = "BUY"
            reason = f"Mocne wyprzedanie (RSI = {rsi})"
        elif prev["SMA10"] <= prev["SMA30"] and latest["SMA10"] > latest["SMA30"]:
            signal = "BUY"
            reason = f"Przecięcie średnich w górę (Golden Cross)"
        elif rsi > 70:
            signal = "SELL"
            reason = f"Mocne wykupienie (RSI = {rsi})"
        elif prev["SMA10"] >= prev["SMA30"] and latest["SMA10"] < latest["SMA30"]:
            signal = "SELL"
            reason = f"Przecięcie średnich w dół"

        max_alloc = INITIAL_CAPITAL * MAX_POSITION_PERCENT
        suggested_shares = int(max_alloc // current_price) if current_price > 0 else 0
        total_cost = round(suggested_shares * current_price, 2)

        return {
            "ticker": symbol.upper(),
            "price": current_price,
            "rsi": rsi,
            "signal": signal,
            "reason": reason,
            "shares": suggested_shares,
            "total_cost": total_cost
        }
    except Exception as e:
        return None

def send_discord_report(results):
    buy_signals = [r for r in results if r and r["signal"] == "BUY"]
    sell_signals = [r for r in results if r and r["signal"] == "SELL"]

    fields = []
    for item in buy_signals[:10]:
        fields.append({
            "name": f"🟢 KUPUJ: {item['ticker']}",
            "value": f"**Cena:** {item['price']} PLN | **RSI:** {item['rsi']}\n"
                     f"**Sugerowana ilość:** {item['shares']} szt. (~{item['total_cost']} PLN)\n"
                     f"**Powód:** {item['reason']}",
            "inline": False
        })

    for item in sell_signals[:10]:
        fields.append({
            "name": f"🔴 SPRZEDAJ: {item['ticker']}",
            "value": f"**Cena:** {item['price']} PLN | **RSI:** {item['rsi']}\n"
                     f"**Powód:** {item['reason']}",
            "inline": False
        })

    total_scanned = len([r for r in results if r])
    desc = f"Przeskanowano **{total_scanned} spółek** z polskiej giełdy (GPW) dla budżetu **{INITIAL_CAPITAL} PLN**.\n"

    if not buy_signals and not sell_signals:
        desc += "ℹ️ *Brak skrajnych sygnałów (RSI < 35 lub > 70). Rynek w fazie konsolidacji.*"
        color = 3447003 
    else:
        color = 3066993 

    payload = {
        "embeds": [{
            "title": "📊 SIGG Bot – Skaner Rynku GPW (Render)",
            "description": desc,
            "color": color,
            "fields": fields,
            "footer": {"text": "SIGG Signal Bot | Chmura Render"}
        }]
    }

    requests.post(DISCORD_WEBHOOK_URL, json=payload)
    print(f"Zakończono! Przeskanowano {total_scanned} spółek i wysłano raport.")

if __name__ == "__main__":
    print("Skanuję polską giełdę na Renderze...")
    reports = []
    for ticker in TICKERS:
        res = analyze_stock(ticker)
        if res:
            reports.append(res)

    send_discord_report(reports)
import yfinance as yf
import pandas as pd
import requests

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1566471711510102102/vVBXiCEShPkZnQFD84U1PTUYOqm1qR3LeYvQu4YcYfBqI8ZcVo5uWlr2KG-UBjgXCH3B"
INITIAL_CAPITAL = 20000 
MAX_POSITION_PERCENT = 0.15  # Max 15% budżetu na jedną spółkę (~3000 zł)

# Lista spółek z GPW z sufiksem .WA dla Yahoo Finance
TICKERS = [
    # WIG20
    "PKO.WA", "PKN.WA", "PZU.WA", "KGH.WA", "PEO.WA", "ALE.WA", "CDR.WA", "LPP.WA", 
    "DNP.WA", "SPL.WA", "ALR.WA", "MBK.WA", "BDX.WA", "KRU.WA", "KTY.WA", "PGE.WA", 
    "TPE.WA", "JSW.WA", "CPS.WA",
    # mWIG40
    "1AT.WA", "ABS.WA", "APR.WA", "APT.WA", "ASB.WA", "ATC.WA", "ATT.WA",
    "BEN.WA", "BFT.WA", "BNP.WA", "BOS.WA", "CCC.WA", "CIG.WA", "CIE.WA", "CMR.WA",
    "DOM.WA", "EAT.WA", "ENA.WA", "EUR.WA", "GTC.WA", "HUG.WA", "ING.WA", 
    "KNT.WA", "MIL.WA", "MOB.WA", "NEU.WA", "PCO.WA", "PCF.WA", "PKP.WA", "PLW.WA", 
    "SNT.WA", "TEN.WA", "TXT.WA", "VRG.WA", "WPP.WA", "XTB.WA", "ZEP.WA",
    # sWIG80 i inne wybrane
    "ACG.WA", "AGO.WA", "AMB.WA", "AMS.WA", "AMR.WA", "BHW.WA", "CLN.WA", "COG.WA",
    "CPG.WA", "ENT.WA", "ERB.WA", "FOR.WA", "GPW.WA", "INC.WA", "IZO.WA", "KGN.WA", 
    "LWB.WA", "MCI.WA", "MGT.WA", "MLS.WA", "MOP.WA", "NNG.WA", "OPN.WA", "PCR.WA", 
    "PNT.WA", "RBW.WA", "ROB.WA", "RVU.WA", "SAN.WA", "SFD.WA", "SHD.WA", "SGP.WA", 
    "SKA.WA", "STH.WA", "STP.WA", "TOR.WA", "UNT.WA", "VOX.WA", "VOT.WA", "WWA.WA"
]

def analyze_stock(symbol):
    try:
        # Pobieranie danych z Yahoo Finance za ostatnie 3 miesiące
        df = yf.download(symbol, period="3mo", interval="1d", progress=False)
        
        if df.empty or len(df) < 30:
            return None

        # Poprawa struktury kolumn w yfinance (czasami zwraca MultiIndex)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)

        if 'Close' not in df.columns:
            return None

        df = df.reset_index()
        close_prices = df["Close"]

        # Ręczne obliczenie RSI (14) żeby nie polegać na zewnętrznych bibliotekach wskaźników
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs))

        # Średnie kroczące SMA 10 i SMA 30
        df["SMA10"] = close_prices.rolling(window=10).mean()
        df["SMA30"] = close_prices.rolling(window=30).mean()

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        current_price = round(float(latest["Close"]), 2)
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
            "ticker": symbol.replace(".WA", "").upper(),
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
    desc = f"Przeskanowano **{total_scanned} spółek** z GPW (Yahoo Finance) dla budżetu **{INITIAL_CAPITAL} PLN**.\n"
    
    if not buy_signals and not sell_signals:
        desc += "ℹ️ *Brak skrajnych sygnałów (RSI < 35 lub > 70). Rynek w fazie konsolidacji.*"
        color = 3447003 
    else:
        color = 3066993 

    payload = {
        "embeds": [{
            "title": "📊 SIGG Bot – Skaner Rynku GPW",
            "description": desc,
            "color": color,
            "fields": fields,
            "footer": {"text": "SIGG Signal Bot | GitHub Actions"}
        }]
    }

    requests.post(DISCORD_WEBHOOK_URL, json=payload)
    print(f"Zakończono! Przeskanowano {total_scanned} spółek i wysłano raport.")

if __name__ == "__main__":
    print("Skanuję polską giełdę przez Yahoo Finance...")
    reports = []
    for ticker in TICKERS:
        res = analyze_stock(ticker)
        if res:
            reports.append(res)
            
    send_discord_report(reports)

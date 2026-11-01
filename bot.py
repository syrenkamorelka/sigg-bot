import yfinance as yf
import pandas as pd
import requests
import json
import os

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1566471711510102102/vVBXiCEShPkZnQFD84U1PTUYOqm1qR3LeYvQu4YcYfBqI8ZcVo5uWlr2KG-UBjgXCH3B"

# Wczytywanie portfela z pliku portfolio.json
PORTFOLIO_FILE = "portfolio.json"

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {"cash": 20000.0, "positions": {}}

# Lista spółek z GPW z sufiksem .WA
TICKERS = [
    "PKO.WA", "PKN.WA", "PZU.WA", "KGH.WA", "PEO.WA", "ALE.WA", "CDR.WA", "LPP.WA", 
    "DNP.WA", "SPL.WA", "ALR.WA", "MBK.WA", "BDX.WA", "KRU.WA", "KTY.WA", "PGE.WA", 
    "TPE.WA", "JSW.WA", "CPS.WA", "1AT.WA", "ABS.WA", "APR.WA", "APT.WA", "ASB.WA", 
    "ATC.WA", "ATT.WA", "BEN.WA", "BFT.WA", "BNP.WA", "BOS.WA", "CCC.WA", "CIG.WA", 
    "CIE.WA", "CMR.WA", "DOM.WA", "EAT.WA", "ENA.WA", "EUR.WA", "GTC.WA", "HUG.WA", 
    "ING.WA", "KNT.WA", "MIL.WA", "MOB.WA", "NEU.WA", "PCO.WA", "PCF.WA", "PKP.WA", 
    "PLW.WA", "SNT.WA", "TEN.WA", "TXT.WA", "VRG.WA", "WPP.WA", "XTB.WA", "ZEP.WA"
]

def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="3mo", interval="1d", progress=False)
        if df.empty or len(df) < 30:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)

        if 'Close' not in df.columns:
            return None

        df = df.reset_index()
        close_prices = df["Close"]

        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs))

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

        return {
            "ticker": symbol.replace(".WA", "").upper(),
            "price": current_price,
            "rsi": rsi,
            "signal": signal,
            "reason": reason
        }
    except Exception as e:
        return None

def send_discord_report(results, portfolio):
    buy_signals = [r for r in results if r and r["signal"] == "BUY"]
    sell_signals = [r for r in results if r and r["signal"] == "SELL"]

    fields = []

    # --- SEKCJA PORTFELA UŻYTKOWNIKA ---
    cash = portfolio["cash"]
    positions = portfolio["positions"]
    
    total_stocks_value = 0
    portfolio_details = ""

    if not positions:
        portfolio_details = "Brak otwartych pozycji (całość w gotówce)."
    else:
        for ticker, data in positions.items():
            shares = data["shares"]
            buy_price = data["buy_price"]
            
            # Pobieramy aktualną cenę dla posiadanej spółki
            current_price = next((r["price"] for r in results if r["ticker"] == ticker), buy_price)
            position_value = shares * current_price
            total_stocks_value += position_value
            
            profit_loss = (current_price - buy_price) * shares
            profit_loss_pct = ((current_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0
            
            emoji = "🟢" if profit_loss >= 0 else "🔴"
            portfolio_details += f"**{ticker}**: {shares} szt. | Cena zakupu: {buy_price} PLN | Akt: {current_price} PLN\n{emoji} Wynik: **{profit_loss:+.2f} PLN ({profit_loss_pct:+.2f}%)**\n\n"

    total_portfolio_value = cash + total_stocks_value
    initial_total = 20000.0  # startowy kapitał
    total_profit_loss = total_portfolio_value - initial_total
    total_profit_loss_pct = (total_profit_loss / initial_total) * 100

    fields.append({
        "name": "💼 Stan Portfela SIGG",
        "value": f"💵 **Gotówka:** {cash:,.2f} PLN\n"
                 f"📈 **Wartość akcji:** {total_stocks_value:,.2f} PLN\n"
                 f"💰 **Całkowity kapitał:** {total_portfolio_value:,.2f} PLN\n"
                 f"📊 **Całkowity wynik:** **{total_profit_loss:+,.2f} PLN ({total_profit_loss_pct:+.2f}%)**\n\n"
                 f"**Posiadane akcje:**\n{portfolio_details}",
        "inline": False
    })

    # --- SEKCJA SYGNAŁÓW RYNKOWYCH ---
    for item in buy_signals[:5]:
        fields.append({
            "name": f"🟢 SYGNAŁ KUPNA: {item['ticker']}",
            "value": f"**Cena:** {item['price']} PLN | **RSI:** {item['rsi']}\n**Powód:** {item['reason']}",
            "inline": False
        })

    for item in sell_signals[:5]:
        fields.append({
            "name": f"🔴 SYGNAŁ SPRZEDAŻY: {item['ticker']}",
            "value": f"**Cena:** {item['price']} PLN | **RSI:** {item['rsi']}\n**Powód:** {item['reason']}",
            "inline": False
        })

    payload = {
        "embeds": [{
            "title": "📊 SIGG Bot – Raport Rynkowy i Portfel",
            "description": f"Automatyczne podsumowanie sesji giełdowej dla portfela SIGG.",
            "color": 3066993,
            "fields": fields,
            "footer": {"text": "SIGG Bot | GitHub Actions"}
        }]
    }

    requests.post(DISCORD_WEBHOOK_URL, json=payload)
    print("Wysłano raport z portfelem na Discorda!")

if __name__ == "__main__":
    print("Skanuję giełdę i obliczam stan portfela...")
    portfolio = load_portfolio()
    reports = []
    for ticker in TICKERS:
        res = analyze_stock(ticker)
        if res:
            reports.append(res)
            
    send_discord_report(reports, portfolio)

import json
import os
import requests
import yfinance as yf

# ==========================================
# KONFIGURACJA I MAPOWANIE RYNKU SIGG
# ==========================================

TICKER_MAP = {
    # Surowce, Górnictwo i Energetyka
    "JSW": "JSW.WA",
    "PGE": "PGE.WA",
    "KGHM": "KGHM.WA",
    "PKNORLEN": "PKN.WA",
    "TAURONPE": "TPE.WA",
    "ENEA": "ENA.WA",
    "BOGDANKA": "LWB.WA",
    "KOGNERERA": "KGN.WA",
    "ZEPAK": "ZEP.WA",
    
    # Banki i Finanse
    "PKOBP": "PKO.WA",
    "PEKAO": "PEO.WA",
    "ALIOR": "ALR.WA",
    "MBANK": "MBK.WA",
    "HANDLOWY": "BHW.WA",
    "MILLENNIUM": "MIL.WA",
    "BNPPPL": "BNP.WA",
    "INGBSK": "ING.WA",
    "QUERCUS": "QRS.WA",
    "GPW": "GPW.WA",
    "KRUK": "KRU.WA",
    "PZU": "PZU.WA",

    # Gry, IT i Nowe Technologie
    "CDPROJEKT": "CDR.WA",
    "11BIT": "11B.WA",
    "PLAYWAY": "PLW.WA",
    "CIGAMES": "CIG.WA",
    "CREEPYJAR": "CRJ.WA",
    "CREOTECH": "CRI.WA",
    "SYGNITY": "SGN.WA",
    "ASSECOPOL": "ACP.WA",
    "ASSECOSEE": "ASE.WA",
    "ASSECOBS": "ABS.WA",
    "COM": "CMP.WA",
    "VERCOM": "VRC.WA",
    "DATAWALK": "DAT.WA",
    "WIRTUALNA": "WPL.WA",
    "XTB": "XTB.WA",
    "VOTUM": "VOT.WA",
    "VOXEL": "VOX.WA",

    # Przemysł, Budownictwo i Handel
    "BUDIMEX": "BDX.WA",
    "LPP": "LPP.WA",
    "DINO": "DNP.WA",
    "ALLEGRO": "ALE.WA",
    "CCC": "CCC.WA",
    "INTERCARS": "CAR.WA",
    "GRUPAPACUJ": "GPP.WA",
    "MURAPOL": "MRP.WA",
    "DEVELA": "DVL.WA",
    "DOMDEV": "DOM.WA",
    "ATAL": "1AT.WA",
    "MIRBUD": "MRB.WA",
    "UNIBEP": "UNI.WA",
    "WIELTON": "WLT.WA",
    "MANDICA": "MNC.WA",
    "FORTE": "FTE.WA",
    "FERRO": "FRO.WA",
    "AMICA": "AMC.WA",
    "AMBRA": "AMB.WA",
    "PEPKOHLD": "PEP.WA",
    "ZABKA": "ZAB.WA",

    # ETF-y z platformy SIGG
    "ETFBW20TR": "ETFBW20TR.WA",
    "ETFBW20ST": "ETFBW20ST.WA",
    "ETFBW20LV": "ETFBW20LV.WA",
    "ETFDAX": "ETFDAX.WA",
    "ETFSP500": "ETFsP500.WA",
    "ETFPZUGOLD": "ETFPZUGOLD.WA",
    "ETFPZUCASH": "ETFPZUCASH.WA",
    "ETFPZUWORLD": "ETFPZUWORLD.WA",
    "ETFBTCPL": "ETFBTCPL.WA",
    "ETFBTBSP": "ETFBTBSP.WA"
}

def load_portfolio():
    """Wczytuje plik portfolio.json z zabezpieczeniami"""
    if not os.path.exists('portfolio.json'):
        print("BŁĄD: Brak pliku portfolio.json!")
        return None
    with open('portfolio.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def run_bot_analysis():
    print("🚀 Uruchamiam zaawansowany silnik analizy giełdowej SIGG...")
    
    portfolio = load_portfolio()
    if not portfolio:
        return

    cash = portfolio.get("cash", 0)
    positions = portfolio.get("positions", {})

    to_sell = []
    portfolio_summary = []
    total_portfolio_value = cash

    # 1. Analiza posiadanych pozycji w portfelu
    for sigg_name, data in positions.items():
        shares = data["shares"]
        buy_price = data["buy_price"]
        
        ticker = TICKER_MAP.get(sigg_name, f"{sigg_name}.WA")
        
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            if hist.empty:
                print(f"⚠️ Brak danych historycznych dla {ticker}")
                continue
            current_price = hist['Close'].iloc[-1]
        except Exception as e:
            print(f"❌ Błąd pobierania ceny dla {ticker}: {e}")
            continue
            
        position_value = shares * current_price
        total_portfolio_value += position_value
        change_pct = ((current_price - buy_price) / buy_price) * 100
        
        portfolio_summary.append({
            "ticker": sigg_name,
            "shares": shares,
            "buy_price": buy_price,
            "current_price": current_price,
            "value": position_value,
            "change": change_pct
        })
        
        # Warunek cięcia strat (Stop-Loss np. przy -5%)
        if change_pct <= -5.0:
            to_sell.append({
                "ticker": sigg_name,
                "shares": shares,
                "buy_price": buy_price,
                "current_price": current_price,
                "change": change_pct
            })

    # 2. Skanowanie kilku wybranych spółek rynkowych pod kątem okazji
    market_highlights = []
    scan_tickers = ["PKN.WA", "PKO.WA", "CDR.WA", "XTB.WA", "ALE.WA"]
    for t in scan_tickers:
        try:
            s = yf.Ticker(t)
            h = s.history(period="5d")
            if not h.empty:
                p_now = h['Close'].iloc[-1]
                p_prev = h['Close'].iloc[0]
                chg = ((p_now - p_prev) / p_prev) * 100
                market_highlights.append({"ticker": t, "price": p_now, "change": chg})
        except:
            pass

    # 3. Budowanie profesjonalnego komunikatu na Discorda
    message = "🤖 **PROFESJONALNY RAPORT GIEŁDOWY SIGG** 📊\n"
    message += "═══════════════════════════════\n\n"

    if len(to_sell) > 0:
        message += "🚨 **ALARM SYSTEMOWY: Wymagana akcja (Cięcie strat):**\n"
        for item in to_sell:
            message += f"• **{item['ticker']}**: Zakup {item['buy_price']} PLN | Obecnie {item['current_price']:.2f} PLN (**{item['change']:.2f}%**)\n"
        message += "\n"
    else:
        message += "🛡️ **Status Portfela:** Wszystkie pozycje bezpieczne. Brak zaleceń sprzedaży na dziś! 💪\n\n"

    message += "📈 **Stan Twoich Aktywów:**\n"
    for item in portfolio_summary:
        icon = "🟢" if item['change'] >= 0 else "🔴"
        message += f"{icon} **{item['ticker']}**: {item['shares']} szt. | Wartość: {item['value']:,.2f} PLN ({item['change']:.2f}%)\n"

    message += f"\n💰 **Wolna gotówka:** {cash:,.2f} PLN\n"
    message += f"💎 **Wartość całkowita portfela:** {total_portfolio_value:,.2f} PLN\n\n"

    if market_highlights:
        message += "🌍 **Skaner Rynku (Wybrane spółki):**\n"
        for mh in market_highlights:
            m_icon = "📈" if mh['change'] >= 0 else "📉"
            message += f"{m_icon} `{mh['ticker']}`: {mh['price']:.2f} PLN ({mh['change']+.2f}%)\n"

    message += "\n═══════════════════════════════\n"
    message += "⚡ *Bot wygenerowany automatycznie przez system SIGG Automation*"

    print(message)

    # 4. Wysyłanie przez Webhook na Discorda
    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    if webhook_url:
        payload = {"content": message}
        response = requests.post(webhook_url, json=payload)
        if response.status_code in [200, 204]:
            print("✅ Pomyślnie wysłano pełny raport na Discorda!")
        else:
            print(f"❌ Błąd wysyłania na Discorda: {response.status_code}")
    else:
        print("⚠️ Brak zmiennej środowiskowej DISCORD_WEBHOOK.")

if __name__ == "__main__":
    run_bot_analysis()

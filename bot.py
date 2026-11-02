import json
import os
import requests
import yfinance as yf

# Mapowanie Twoich spółek z portfela SIGG
TICKER_MAP = {
    "JSW": "JSW.WA",
    "PGE": "PGE.WA",
    "KGHM": "KGHM.WA",
    "PZU": "PZU.WA",
    "TAURONPE": "TPE.WA"
}

def run_bot():
    print("🚀 Uruchamiam skaner portfela SIGG...")
    
    if not os.path.exists('portfolio.json'):
        print("❌ BŁĄD: Brak pliku portfolio.json!")
        return

    with open('portfolio.json', 'r', encoding='utf-8') as f:
        portfolio = json.load(f)

    cash = portfolio.get("cash", 0)
    positions = portfolio.get("positions", {})

    to_sell = []
    portfolio_summary = []
    total_portfolio_value = cash

    for sigg_name, data in positions.items():
        shares = data["shares"]
        buy_price = data["buy_price"]
        
        ticker = TICKER_MAP.get(sigg_name, f"{sigg_name}.WA")
        print(f"Pobieram dane dla {ticker}...")
        
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            if hist.empty:
                print(f"⚠️ Brak danych dla {ticker}")
                continue
            current_price = hist['Close'].iloc[-1]
        except Exception as e:
            print(f"❌ Błąd pobierania {ticker}: {e}")
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
        
        # Stop-loss przy -5%
        if change_pct <= -5.0:
            to_sell.append({
                "ticker": sigg_name,
                "shares": shares,
                "buy_price": buy_price,
                "current_price": current_price,
                "change": change_pct
            })

    # Budowanie wiadomości
    message = "🤖 **RAPORT GIEŁDOWY SIGG** 📊\n\n"

    if len(to_sell) > 0:
        message += "🚨 **ALARM: Wymagana sprzedaż (Cięcie strat):**\n"
        for item in to_sell:
            message += f"• **{item['ticker']}**: Zakup {item['buy_price']} PLN | Obecnie {item['current_price']:.2f} PLN (**{item['change']:.2f}%**)\n"
        message += "\n"
    else:
        message += "🛡️ **Status Portfela:** Wszystkie pozycje stabilne. Brak zaleceń sprzedaży na dzisiaj! 💪\n\n"

    message += "📈 **Twoje aktywa:**\n"
    for item in portfolio_summary:
        icon = "🟢" if item['change'] >= 0 else "🔴"
        message += f"{icon} **{item['ticker']}**: {item['shares']} szt. | Wartość: {item['value']:,.2f} PLN ({item['change']:.2f}%)\n"

    message += f"\n💰 **Gotówka:** {cash:,.2f} PLN\n"
    message += f"💎 **Wartość portfela:** {total_portfolio_value:,.2f} PLN"

    print("Gotowa wiadomość do wysłania:")
    print(message)

    # Wysyłanie na Discorda
    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    if webhook_url:
        payload = {"content": message}
        response = requests.post(webhook_url, json=payload)
        printzesz status HTTP:", response.status_code)
        if response.status_code in [200, 204]:
            print("✅ Wiadomość pomyślnie dostarczona na Discorda!")
        else:
            print(f"❌ Discord odrzucił wiadomość. Kod: {response.status_code}, Treść: {response.text}")
    else:
        print("❌ KRYTYCZNY BŁĄD: Zmienna DISCORD_WEBHOOK nie jest widoczna w GitHub Actions!")

if __name__ == "__main__":
    run_bot()

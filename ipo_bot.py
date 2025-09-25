import requests
from bs4 import BeautifulSoup
import asyncio
from telegram import Bot
import os
from datetime import datetime

# Scrape Mainboard IPOs
def scrape_ipo():
    url = "https://www.chittorgarh.com/calendar/ipo-calendar/1/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/116.0.0.0 Safari/537.36"
    }

    res = requests.get(url, headers=headers)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    table = soup.find("table", class_="tblIPO")
    if not table:
        print("Could not find IPO table on the page.")
        return []

    ipo_list = []
    for row in table.find("tbody").find_all("tr"):
        cols = row.find_all("td")
        if len(cols) != 10:
            continue
        try:
            ipo_data = {
                "name": cols[0].text.strip(),
                "open_date": datetime.strptime(cols[1].text.strip(), "%d-%m-%Y"),
                "close_date": datetime.strptime(cols[2].text.strip(), "%d-%m-%Y"),
                "gmp": float(cols[3].text.strip().replace('%','')) if cols[3].text.strip() else 0,
                "retail_shares": cols[4].text.strip(),
                "retail_amount": cols[5].text.strip(),
                "hni_shares": cols[6].text.strip(),
                "hni_amount": cols[7].text.strip(),
                "bhni_shares": cols[8].text.strip(),
                "bhni_amount": cols[9].text.strip()
            }
            ipo_list.append(ipo_data)
        except Exception as e:
            print("Error parsing row:", e)
            continue

    return ipo_list

# Filter IPOs currently open and GMP > 10%
def select_open_ipos(ipo_list):
    today = datetime.today()
    filtered = [
        ipo for ipo in ipo_list
        if ipo['gmp'] > 10 and ipo['open_date'] <= today <= ipo['close_date']
    ]
    filtered.sort(key=lambda x: x['gmp'], reverse=True)
    return filtered

# Compose Telegram message
def compose_message(ipos):
    if not ipos:
        return "📢 No Mainboard IPOs currently open with GMP >10% today."

    total_fund = 0
    msg = "📢 Current Mainboard IPOs (Open & GMP >10%):\n\n"

    for ipo in ipos:
        msg += f"{ipo['name']}\n"
        msg += f"   - Opening: {ipo['open_date'].strftime('%d-%m-%Y')}\n"
        msg += f"   - Closing: {ipo['close_date'].strftime('%d-%m-%Y')}\n"
        msg += f"   - GMP: {ipo['gmp']}%\n"
        msg += f"   - Retail: {ipo['retail_shares']} shares → {ipo['retail_amount']}\n"
        msg += f"   - HNI: {ipo['hni_shares']} shares → {ipo['hni_amount']}\n"
        msg += f"   - BHNI: {ipo['bhni_shares']} shares → {ipo['bhni_amount']}\n\n"
        total_fund += 10_00_000  # 10 Lacs per IPO

    msg += f"💰 Total Fund Required: ₹{total_fund:,}\n"
    return msg

# Main async function
async def main():
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    ipo_list = scrape_ipo()
    open_ipos = select_open_ipos(ipo_list)
    message = compose_message(open_ipos)

    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=chat_id, text=message)

# Run the async function
if __name__ == "__main__":
    asyncio.run(main())

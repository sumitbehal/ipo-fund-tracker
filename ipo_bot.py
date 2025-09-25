import os
import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Bot

# -------------------------
# Load secrets
# -------------------------
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

if not bot_token or not chat_id:
    raise ValueError("Bot token or chat ID not found in environment variables!")

# -------------------------
# Chittorgarh IPO scraping
# -------------------------
URL = "https://www.chittorgarh.com/report/ipo-calendar/"

def scrape_ipo():
    res = requests.get(URL)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    ipo_data = []

    # The IPO table is usually the first table with class 'table' (verify on website)
    table = soup.find("table", class_="table")
    if not table:
        print("No table found on the page!")
        return ipo_data

    rows = table.find_all("tr")[1:]  # skip header

    for row in rows:
        cols = [c.get_text(strip=True) for c in row.find_all("td")]
        if len(cols) < 12:
            continue

        ipo_type = cols[2]  # Type column
        if "Mainboard" not in ipo_type:
            continue  # skip non-mainboard IPOs

        try:
            ipo = {
                "name": cols[0],
                "opening_date": cols[4],
                "closing_date": cols[5],
                "issue_price": float(cols[6].replace(",", "")),
                "retail_shares": int(cols[7].replace(",", "")),
                "hni_shares": int(cols[8].replace(",", "")),
                "bhni_shares": int(cols[9].replace(",", "")),
                "gmp": float(cols[10].replace("%", "")) if cols[10] else 0,
            }
            ipo_data.append(ipo)
        except Exception as e:
            print(f"Skipping row due to error: {e}")

    return ipo_data

# -------------------------
# Calculate fund
# -------------------------
def calculate_fund(ipo_data):
    message_lines = []
    total_fund = 0

    for ipo in ipo_data:
        if ipo["gmp"] < 10:
            continue  # Only consider GMP > 10%

        retail_amount = ipo["issue_price"] * ipo["retail_shares"]
        hni_amount = ipo["issue_price"] * ipo["hni_shares"]
        bhni_amount = ipo["issue_price"] * ipo["bhni_shares"]

        total_fund += retail_amount + hni_amount + bhni_amount

        lines = [
            f"{ipo['name']}",
            f"   - Opening: {ipo['opening_date']}",
            f"   - Closing: {ipo['closing_date']}",
            f"   - GMP: {ipo['gmp']}%",
            f"   - Retail: {ipo['retail_shares']} shares → ₹{retail_amount:,}",
            f"   - HNI: {ipo['hni_shares']} shares → ₹{hni_amount:,}",
            f"   - BHNI: {ipo['bhni_shares']} shares → ₹{bhni_amount:,}",
        ]
        message_lines.append("\n".join(lines))

    return total_fund, message_lines

# -------------------------
# Telegram async function
# -------------------------
async def main():
    bot = Bot(token=bot_token)

    ipo_data = scrape_ipo()
    if not ipo_data:
        await bot.send_message(chat_id=chat_id, text="No Mainboard IPOs found today.")
        return

    total_fund, message_lines = calculate_fund(ipo_data)

    if total_fund == 0:
        await bot.send_message(chat_id=chat_id, text="No Mainboard IPOs require funds today (GMP < 10%).")
        return

    message = "📢 Today's Mainboard IPO Fund Update:\n\n"
    message += "\n\n".join(message_lines)
    message += f"\n\n💰 Total Fund Required: ₹{total_fund:,}"

    await bot.send_message(chat_id=chat_id, text=message)
    print("Message sent successfully!")

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import os
import re
from datetime import datetime
from playwright.async_api import async_playwright
from telegram import Bot

URL = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"
DATE_FORMAT = "%d-%b-%Y"  # e.g. 25-Sep-2025

async def scrape_live_ipos():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # Navigate to the live GMP page and wait for network to be idle
        await page.goto(URL, wait_until="networkidle")
        # Wait additional time for JavaScript to populate the table
        await asyncio.sleep(10)
        # Select all rows from the mainboard GMP table
        rows = await page.query_selector_all("table tbody tr")
        ipo_list = []
        for row in rows:
            cells = await row.query_selector_all("td")
            # Skip rows that don’t have the expected number of columns
            if len(cells) < 10:
                continue
            try:
                name = (await cells[0].inner_text()).strip()
                gmp_text = (await cells[1].inner_text()).strip()
                # Extract percentage inside parentheses, e.g. “₹80 (16.13%)”
                m = re.search(r'\(([-+]?\d+\.?\d*)%', gmp_text)
                gmp_percent = float(m.group(1)) if m else 0.0
                open_date_str = (await cells[8].inner_text()).strip()
                close_date_str = (await cells[9].inner_text()).strip()
                # Convert “23-Sep” to a full date this year
                year = datetime.now().year
                open_date = datetime.strptime(f"{open_date_str}-{year}", DATE_FORMAT)
                close_date = datetime.strptime(f"{close_date_str}-{year}", DATE_FORMAT)
                ipo_list.append({
                    "name": name,
                    "gmp_percent": gmp_percent,
                    "open_date": open_date,
                    "close_date": close_date
                })
            except Exception:
                continue
        await browser.close()
        return ipo_list

def filter_current_ipos(ipos):
    """Return IPOs that are open today (open_date ≤ today ≤ close_date) and have GMP > 10%."""
    today = datetime.now().date()
    return [
        ipo for ipo in ipos
        if ipo["gmp_percent"] > 10
        and ipo["open_date"].date() <= today <= ipo["close_date"].date()
    ]

def compose_telegram_message(ipos):
    """Construct a message summarizing eligible IPOs and total funds needed."""
    if not ipos:
        return "📢 No live IPOs with GMP > 10% are open today."
    message_lines = ["📢 Current live Mainboard IPOs with GMP > 10% and open today:\n"]
    total_fund = 0
    for ipo in ipos:
        message_lines.append(
            f"• {ipo['name']}: GMP {ipo['gmp_percent']:.2f}%, "
            f"Open {ipo['open_date'].strftime('%d-%b')}, "
            f"Close {ipo['close_date'].strftime('%d-%b')}"
        )
        total_fund += 10_00_000  # ₹10 lakh per IPO
    message_lines.append(f"\n💰 Total fund required: ₹{total_fund:,}")
    return "\n".join(message_lines)

async def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    ipo_list = await scrape_live_ipos()
    eligible = filter_current_ipos(ipo_list)
    message = compose_telegram_message(eligible)
    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=chat_id, text=message)

if __name__ == "__main__":
    asyncio.run(main())

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
        await page.goto(URL, wait_until="networkidle")

        # wait for JS to render
        await asyncio.sleep(10)

        rows = await page.query_selector_all("table tbody tr")
        ipo_list = []
        for row in rows:
            cells = await row.query_selector_all("td")
            if len(cells) < 10:
                continue
            try:
                name = (await cells[0].inner_text()).strip()
                gmp_text = (await cells[1].inner_text()).strip()
                m = re.search(r'\(([-+]?\d+\.?\d*)%', gmp_text)
                gmp_percent = float(m.group(1)) if m else 0.0

                open_date_str = (await cells[8].inner_text()).strip()
                close_date_str = (await cells[9].inner_text()).strip()
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
    today = datetime.now().date()
    return [
        ipo for ipo in ipos
        if ipo["gmp_percent"] > 10
        and ipo["open_date"].date() <= today <= ipo["close_date"].date()
    ]

def compose_telegram_message(ipos):
    if not ipos:
        return "📢 No live IPOs with GMP > 10% are open today."

    msg = "📢 Live Mainboard IPOs (GMP > 10%)\n\n"
    total_fund = 0

    for ipo in ipos:
        msg += f"**{ipo['name']}**\n"
        msg += f"▫️ GMP: **{ipo['gmp_percent']:.2f}%**\n"
        msg += f"▫️ Open: {ipo['open_date'].strftime('%d-%b')} → Close: {ipo['close_date'].strftime('%d-%b')}\n\n"
        total_fund += 10_00_000

    msg += f"**💰 Total Fund Required: ₹{total_fund:,}**"
    return msg

async def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    ipo_list = await scrape_live_ipos()
    eligible = filter_current_ipos(ipo_list)
    message = compose_telegram_message(eligible)

    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")

if __name__ == "__main__":
    asyncio.run(main())

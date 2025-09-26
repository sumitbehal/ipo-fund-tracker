import asyncio
import os
import re
import math
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
            # Expect at least 10 cells: name, gmp, rating, sub, gmp(l/h), price, ipo size, lot, open, close
            if len(cells) < 10:
                continue
            try:
                name = (await cells[0].inner_text()).strip()

                # Extract GMP % from the second column (₹ value + percentage)
                gmp_text = (await cells[1].inner_text()).strip()
                m = re.search(r'\(([-+]?\d+\.?\d*)%', gmp_text)
                gmp_percent = float(m.group(1)) if m else 0.0

                # Price band/price column (cell index 5). Take the highest numeric value.
                price_text = (await cells[5].inner_text()).strip()
                # Remove commas and extract all numbers (handles ranges like “100 / 105”)
                price_numbers = re.findall(r'\d+(?:\.\d+)?', price_text.replace(',', ''))
                price = max([float(n) for n in price_numbers]) if price_numbers else None

                # Lot size column (cell index 7)
                lot_text = (await cells[7].inner_text()).strip()
                m_lot = re.search(r'\d+', lot_text.replace(',', ''))
                lot_size = int(m_lot.group()) if m_lot else None

                # Open/close dates
                open_date_str = (await cells[8].inner_text()).strip()
                close_date_str = (await cells[9].inner_text()).strip()
                year = datetime.now().year
                open_date = datetime.strptime(f"{open_date_str}-{year}", DATE_FORMAT)
                close_date = datetime.strptime(f"{close_date_str}-{year}", DATE_FORMAT)
                # If the close date appears earlier in the calendar year than the open date, assume it wraps to next year
                if close_date < open_date:
                    close_date = datetime.strptime(f"{close_date_str}-{year+1}", DATE_FORMAT)

                ipo_list.append({
                    "name": name,
                    "gmp_percent": gmp_percent,
                    "open_date": open_date,
                    "close_date": close_date,
                    "price": price,        # per-share price (upper band)
                    "lot_size": lot_size   # number of shares per lot
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
    total_retail = 0
    total_shni   = 0
    total_bhni   = 0

    for ipo in ipos:
        name = ipo['name']
        gmp = ipo['gmp_percent']
        price = ipo.get('price')
        lot = ipo.get('lot_size')
        open_date = ipo['open_date']
        close_date = ipo['close_date']

        msg += f"**{name}**\n"
        msg += f"▫️ GMP: **{gmp:.2f}%**\n"
        msg += f"▫️ Open: {open_date.strftime('%d-%b')} → Close: {close_date.strftime('%d-%b')}\n"

        # Only compute funds if price and lot size are available
        if price and lot:
            share_cost = price * lot

            # Retail: 1 lot
            retail_funds = share_cost

            # S-HNI: 14 lots, but if 14-lot cost > 2,00,000, use 13 lots
            shni_lots = 14
            if share_cost * shni_lots > 200_000:
                shni_lots = 13
            shni_funds = share_cost * shni_lots

            # B-HNI: first multiple of lot after 10,00,000
            bhni_lots = math.ceil(1_000_000 / share_cost)
            bhni_funds = share_cost * bhni_lots

            msg += (
                f"▫️ Price: ₹{price:.2f} | Lot Size: {lot}\n"
                f"▫️ Funds Required → "
                f"Retail: ₹{retail_funds:,.0f}, "
                f"S-HNI: ₹{shni_funds:,.0f}, "
                f"B-HNI: ₹{bhni_funds:,.0f}\n\n"
            )

            total_retail += retail_funds
            total_shni   += shni_funds
            total_bhni   += bhni_funds
        else:
            # missing price/lot — skip calculations
            msg += "▫️ Price/Lot information not available\n\n"

    msg += f"**💰 Total Retail Funds (all IPOs): ₹{total_retail:,.0f}**\n"
    msg += f"**💰 Total S-HNI Funds (all IPOs): ₹{total_shni:,.0f}**\n"
    msg += f"**💰 Total B-HNI Funds (all IPOs): ₹{total_bhni:,.0f}**"
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

import asyncio
from telegram import Bot
import os
from playwright.async_api import async_playwright

URL = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"

async def scrape_live_ipos():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")

        # Wait longer for JS table to load
        await asyncio.sleep(10)

        # Use a general selector for table rows
        rows = await page.query_selector_all("table tbody tr")
        if not rows:
            print("No IPO rows found. Table may not be loaded yet.")
            await browser.close()
            return []

        ipo_list = []

        for row in rows:
            cols = await row.query_selector_all("td")
            if len(cols) < 6:
                continue
            try:
                # Extract GMP safely
                gmp_td = await cols[1].query_selector("span")
                gmp_text = (
                    (await gmp_td.inner_text()).replace('%','').replace(',','').strip()
                    if gmp_td else (await cols[1].inner_text()).replace('%','').replace(',','').strip()
                )
                gmp_value = float(gmp_text) if gmp_text and gmp_text != '--' else 0

                ipo = {
                    "name": (await cols[0].inner_text()).strip(),
                    "gmp": gmp_value,
                    "retail_shares": (await cols[2].inner_text()).strip(),
                    "retail_amount": (await cols[3].inner_text()).strip(),
                    "hni_shares": (await cols[4].inner_text()).strip(),
                    "hni_amount": (await cols[5].inner_text()).strip(),
                }
                ipo_list.append(ipo)
            except Exception as e:
                print("Error parsing row:", e)
                continue

        await browser.close()
        return ipo_list

def filter_ipos(ipo_list):
    # Only GMP > 10%
    filtered = [ipo for ipo in ipo_list if ipo['gmp'] > 10]
    filtered.sort(key=lambda x: x['gmp'], reverse=True)
    return filtered

def compose_message(ipos):
    if not ipos:
        return "📢 No live IPOs with GMP >10% today."

    total_fund = 0
    msg = "📢 Current Live Mainboard IPOs (GMP >10%):\n\n"

    for ipo in ipos:
        msg += f"{ipo['name']}\n"
        msg += f"   - GMP: {ipo['gmp']}%\n"
        msg += f"   - Retail: {ipo['retail_shares']} → {ipo['retail_amount']}\n"
        msg += f"   - HNI: {ipo['hni_shares']} → {ipo['hni_amount']}\n\n"
        total_fund += 10_00_000  # 10 Lacs per IPO

    msg += f"💰 Total Fund Required: ₹{total_fund:,}\n"
    return msg

async def main():
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    ipo_list = await scrape_live_ipos()

    # DEBUG: print all scraped IPOs
    print("DEBUG: All IPOs scraped:")
    for ipo in ipo_list:
        print(f"{ipo['name']} - GMP: {ipo['gmp']}%")

    filtered_ipos = filter_ipos(ipo_list)
    message = compose_message(filtered_ipos)

    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=chat_id, text=message)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import os
import re
import math
from datetime import datetime
from playwright.async_api import async_playwright
from telegram import Bot

URL = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"
DATE_FORMAT = "%d-%b-%Y"  # e.g. 25-Sep-2025


# ---------- Helpers (Indian numbering) ----------
def format_inr_number(n, decimals=0):
    """Format number with Indian comma system (e.g., 3026376 -> 30,26,376)."""
    if n is None:
        return "-"
    neg = n < 0
    n = abs(n)
    s = f"{n:.{decimals}f}"
    if "." in s:
        int_part, frac = s.split(".")
    else:
        int_part, frac = s, ""
    if len(int_part) > 3:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        int_part = ",".join(groups + [last3])
    out = int_part
    if decimals > 0:
        out += "." + frac
    if neg:
        out = "-" + out
    return out


def money_inr(n, decimals=0):
    if n is None:
        return "₹-"
    return f"₹{format_inr_number(n, decimals)}"


def clean_ipo_name(raw: str) -> str:
    if not raw:
        return raw
    s = raw.strip()
    s = re.sub(r"\s+IPO\s*[A-Z]?$", " IPO", s, flags=re.IGNORECASE)
    if not s.upper().endswith("IPO"):
        s = s.rstrip() + " IPO"
    return s.strip()


# ---------- Scraper (Hardened + Debugging) ----------
async def scrape_live_ipos():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        
        # CHANGE 1: Use a standard Windows Desktop User Agent & Viewport
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="Asia/Kolkata"
        )

        # Block heavy assets to speed up loading
        async def _route(route):
            req = route.request
            if req.resource_type in {"image", "media", "font", "stylesheet"}:
                await route.abort()
            else:
                await route.continue_()
        await context.route("**/*", _route)

        page = await context.new_page()
        page.set_default_timeout(60_000)

        ipo_list = []

        try:
            # CHANGE 2: Wait for network idle to ensure anti-bot scripts finish
            await page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
            
            try:
                await page.wait_for_load_state("networkidle", timeout=10_000)
            except Exception:
                pass  # Ignore network idle timeout, proceed to selector check

            # CHANGE 3: The Wait - Wrapped in error handling for debugging
            await page.wait_for_selector("table tbody tr", timeout=60_000)

            rows = await page.query_selector_all("table tbody tr")
            
            for row in rows:
                cells = await row.query_selector_all("td")
                if len(cells) < 10:
                    continue
                try:
                    raw_name = (await cells[0].inner_text()).strip()
                    name = clean_ipo_name(raw_name)

                    gmp_text = (await cells[1].inner_text()).strip()
                    m = re.search(r"\(([-+]?\d+\.?\d*)\s*%", gmp_text)
                    gmp_percent = float(m.group(1)) if m else 0.0

                    price_text = (await cells[5].inner_text()).strip()
                    nums = re.findall(r"\d+(?:\.\d+)?", price_text.replace(",", ""))
                    price = max([float(x) for x in nums]) if nums else None

                    lot_text = (await cells[7].inner_text()).strip()
                    mlot = re.search(r"\d+", lot_text.replace(",", ""))
                    lot_size = int(mlot.group()) if mlot else None

                    open_date_str = (await cells[8].inner_text()).strip()
                    close_date_str = (await cells[9].inner_text()).strip()
                    year = datetime.now().year
                    
                    try:
                        open_date = datetime.strptime(f"{open_date_str}-{year}", DATE_FORMAT)
                        close_date = datetime.strptime(f"{close_date_str}-{year}", DATE_FORMAT)
                        if close_date < open_date:
                            close_date = datetime.strptime(f"{close_date_str}-{year+1}", DATE_FORMAT)
                    except ValueError:
                        continue # Skip rows with invalid dates

                    ipo_list.append({
                        "name": name,
                        "gmp_percent": gmp_percent,
                        "open_date": open_date,
                        "close_date": close_date,
                        "price": price,
                        "lot_size": lot_size
                    })
                except Exception:
                    continue

        except Exception as e:
            print(f"❌ Error encountered: {e}")
            # CHANGE 4: Capture Screenshot and HTML for debugging
            await page.screenshot(path="error_screenshot.png")
            with open("error_page.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
            print("📸 Saved error_screenshot.png and error_page.html for debugging.")
            raise e  # Re-raise to fail the workflow

        finally:
            await browser.close()

        return ipo_list


# ---------- Filters (unchanged) ----------
def filter_current_ipos(ipos):
    today = datetime.now().date()
    return [
        ipo for ipo in ipos
        if ipo["gmp_percent"] > 10
        and ipo["open_date"].date() <= today <= ipo["close_date"].date()
    ]


# ---------- Message builder (unchanged) ----------
def compose_telegram_message(ipos):
    if not ipos:
        return "📢 No live IPOs with GMP > 10% are open today."

    header = "📢 Live IPOs (GMP > 10%)\n\n"
    body_parts = []

    total_retail = 0
    total_shni = 0
    total_bhni = 0

    for ipo in ipos:
        name = ipo["name"]
        gmp = ipo["gmp_percent"]
        price = ipo.get("price")
        lot = ipo.get("lot_size")
        open_dt = ipo["open_date"].strftime("%d-%b-%Y")
        close_dt = ipo["close_date"].strftime("%d-%b-%Y")

        section = []
        section.append("━━━━━━━━━━━━━━━━━━━━")
        section.append(f"📌 {name}")
        section.append("━━━━━━━━━━━━━━━━━━━━")
        section.append(f"▫️ GMP: **{gmp:.2f}%**")
        section.append(f"▫️ Open: {open_dt} → Close: {close_dt}")

        if price and lot:
            section.append(f"▫️ Price: {money_inr(price, 2)} | Lot Size: {format_inr_number(lot)}")
            lot_cost = price * lot

            retail_lots = 1
            retail_funds = lot_cost
            retail_shares = lot * retail_lots

            shni_lots = 14
            if lot_cost * shni_lots > 200_000:
                shni_lots = 13
            shni_funds = lot_cost * shni_lots
            shni_shares = lot * shni_lots

            bhni_lots = math.ceil(1_000_000 / lot_cost)
            bhni_funds = lot_cost * bhni_lots
            bhni_shares = lot * bhni_lots

            section.append(f"👤 Retail: {money_inr(retail_funds)}  ({format_inr_number(retail_shares)} shares)")
            section.append(f"👥 S-HNI : {money_inr(shni_funds)}  ({format_inr_number(shni_shares)} shares)")
            section.append(f"🏦 B-HNI : {money_inr(bhni_funds)}  ({format_inr_number(bhni_shares)} shares)")

            total_retail += retail_funds
            total_shni += shni_funds
            total_bhni += bhni_funds
        else:
            section.append("_Price/Lot information not available_")

        section.append("") 
        body_parts.append("\n".join(section))

    totals = []
    totals.append("==========================")
    totals.append("💰 TOTAL FUNDS (All IPOs)")
    totals.append(f"👤 Retail: {money_inr(total_retail)}")
    totals.append(f"👥 S-HNI : {money_inr(total_shni)}")
    totals.append(f"🏦 B-HNI : {money_inr(total_bhni)}")
    totals.append("==========================")

    return header + "\n".join(body_parts) + "\n" + "\n".join(totals)


# ---------- Main ----------
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

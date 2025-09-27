import asyncio
import os
import re
import math
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from playwright.async_api import async_playwright
from telegram import Bot

URL = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"
DATE_FORMAT = "%d-%b-%Y"
IST = ZoneInfo("Asia/Kolkata")
STATE_FILE = Path(".state/last_hash.txt")

# ---------- Helpers ----------
def format_inr_number(n, decimals=0):
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
        s = s + " IPO"
    return s.strip()

# ---------- Scraper ----------
async def scrape_live_ipos():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0",
            extra_http_headers={"Cache-Control": "no-cache"}
        )
        page = await context.new_page()
        page.set_default_timeout(60_000)

        await page.goto(f"{URL}?t={int(datetime.now().timestamp())}", wait_until="domcontentloaded")
        await page.wait_for_selector("table tbody tr")

        rows = await page.query_selector_all("table tbody tr")
        ipo_list = []
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
                year = datetime.now(IST).year
                open_date = datetime.strptime(f"{open_date_str}-{year}", DATE_FORMAT)
                close_date = datetime.strptime(f"{close_date_str}-{year}", DATE_FORMAT)
                if close_date < open_date:
                    close_date = datetime.strptime(f"{close_date_str}-{year+1}", DATE_FORMAT)

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

        await browser.close()
        return ipo_list

# ---------- Filters ----------
def filter_current_ipos(ipos):
    today = datetime.now(IST).date()
    return [
        ipo for ipo in ipos
        if ipo["gmp_percent"] > 10
        and ipo["open_date"].date() <= today <= ipo["close_date"].date()
    ]

# ---------- Message builder ----------
def compose_message(ipos):
    if not ipos:
        return "📢 No live IPOs with GMP > 10% are open today."

    header = "📢 Live IPOs (GMP > 10%)\n\n"
    body_parts = []
    total_retail = total_shni = total_bhni = 0

    for ipo in ipos:
        name, gmp, price, lot = ipo["name"], ipo["gmp_percent"], ipo.get("price"), ipo.get("lot_size")
        open_dt, close_dt = ipo["open_date"].strftime("%d-%b-%Y"), ipo["close_date"].strftime("%d-%b-%Y")

        section = [
            "━━━━━━━━━━━━━━━━━━━━",
            f"📌 {name}",
            "━━━━━━━━━━━━━━━━━━━━",
            f"▫️ GMP: **{gmp:.2f}%**",
            f"▫️ Open: {open_dt} → Close: {close_dt}"
        ]

        if price and lot:
            section.append(f"▫️ Price: {money_inr(price, 2)} | Lot Size: {format_inr_number(lot)}")
            lot_cost = price * lot

            # Retail
            section.append(f"👤 Retail: {money_inr(lot_cost)}  ({format_inr_number(lot)} shares)")
            total_retail += lot_cost

            # S-HNI
            shni_lots = 14 if lot_cost * 14 <= 200_000 else 13
            shni_funds = lot_cost * shni_lots
            section.append(f"👥 S-HNI : {money_inr(shni_funds)}  ({format_inr_number(lot*shni_lots)} shares)")
            total_shni += shni_funds

            # B-HNI
            bhni_lots = math.ceil(1_000_000 / lot_cost)
            bhni_funds = lot_cost * bhni_lots
            section.append(f"🏦 B-HNI : {money_inr(bhni_funds)}  ({format_inr_number(lot*bhni_lots)} shares)")
            total_bhni += bhni_funds
        else:
            section.append("_Price/Lot info not available_")

        body_parts.append("\n".join(section) + "\n")

    totals = [
        "==========================",
        "💰 TOTAL FUNDS (All IPOs)",
        f"👤 Retail: {money_inr(total_retail)}",
        f"👥 S-HNI : {money_inr(total_shni)}",
        f"🏦 B-HNI : {money_inr(total_bhni)}",
        "==========================",
    ]

    return header + "\n".join(body_parts) + "\n".join(totals)

# ---------- Duplicate guard ----------
def already_sent(message: str) -> bool:
    new_hash = hashlib.sha256(message.encode("utf-8")).hexdigest()
    if STATE_FILE.exists():
        old_hash = STATE_FILE.read_text().strip()
        if new_hash == old_hash:
            return True
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(new_hash)
    return False

# ---------- Main ----------
async def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    ipo_list = await scrape_live_ipos()
    eligible = filter_current_ipos(ipo_list)
    message = compose_message(eligible)

    if already_sent(message):
        print("⚠️ No change since last run → skipping post.")
        return

    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
    print("✅ Posted to Telegram.")

if __name__ == "__main__":
    asyncio.run(main())

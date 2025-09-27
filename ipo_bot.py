import asyncio
import os
import re
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

URL = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"
DATE_FORMAT = "%d-%b-%Y"
IST = ZoneInfo("Asia/Kolkata")

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
    # Remove trailing "IPO X"
    s = re.sub(r"\s+IPO\s*[A-Z]?$", " IPO", s, flags=re.IGNORECASE)
    if not s.upper().endswith("IPO"):
        s = s + " IPO"
    return s.strip()

# ---------- Scraper ----------
async def scrape_live_ipos():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (X11; Linux x86_64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"),
            viewport={"width": 1280, "height": 1800},
            extra_http_headers={"Cache-Control": "no-cache", "Pragma": "no-cache"}
        )
        async def _route(route):
            if route.request.resource_type in {"image", "media", "font", "stylesheet"}:
                await route.abort()
            else:
                await route.continue_()
        await context.route("**/*", _route)

        page = await context.new_page()
        page.set_default_timeout(60_000)

        for attempt in range(3):
            try:
                cache_bust = f"{URL}?t={int(datetime.now().timestamp())}"
                await page.goto(cache_bust, wait_until="domcontentloaded", timeout=60_000)
                await page.wait_for_selector("table tbody tr", timeout=60_000)
                break
            except Exception:
                if attempt == 2:

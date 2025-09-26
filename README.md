IPO Funds Tracker Bot

📢 Automated Telegram bot that posts daily updates on active Mainboard IPOs in India with GMP > 10%.
It calculates and displays the funds required for different investor categories:

👤 Retail (1 lot)

👥 S-HNI (13–14 lots, capped at ₹2,00,000)

🏦 B-HNI (minimum lots required beyond ₹10,00,000)

👉 Join the channel here: t.me/ipofunds

Features

Scrapes live IPO data from Investorgain

Calculates fund requirements + share count for Retail, S-HNI, and B-HNI

Aggregates totals across all eligible IPOs

Sends a formatted message daily at 10:00 AM IST to a Telegram channel

Built with Python, Playwright, and python-telegram-bot

Runs automatically on GitHub Actions (no server required)

Example Output
📢 Live IPOs (GMP > 10%)

📌 Pace Digitek IPO
▫️ GMP: 14.61%
▫️ Open: 26-Sep-2025 → Close: 30-Sep-2025
▫️ Price: ₹219.00 | Lot Size: 68
👤 Retail: ₹14,892  (68 shares)
👥 S-HNI : ₹1,93,596  (952 shares)
🏦 B-HNI : ₹10,12,656  (4,624 shares)

💰 TOTAL FUNDS (All IPOs)
👤 Retail: ₹44,292
👥 S-HNI : ₹5,75,796
🏦 B-HNI : ₹30,26,376


Workflow runs daily at 10 AM IST via GitHub Actions.

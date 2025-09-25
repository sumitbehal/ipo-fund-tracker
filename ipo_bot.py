import os
from telegram import Bot

bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

print("Bot token:", bot_token)
print("Chat ID:", chat_id)

if not bot_token or not chat_id:
    raise ValueError("Bot token or chat ID not found in environment variables!")

bot = Bot(token=bot_token)
bot.send_message(chat_id=chat_id, text="✅ Test message from your Telegram bot is working!")
print("Message sent successfully!")

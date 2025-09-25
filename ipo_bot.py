import os
from telegram import Bot

# Load secrets from GitHub Actions
bot_token = os.getenv("8287714366:AAF9fWj595ToFnphCEJwFHv8022uBCH03WY")
chat_id = os.getenv("1707794890")

bot = Bot(token=bot_token)

# Send test message
bot.send_message(chat_id=chat_id, text="✅ Test message from your Telegram bot is working!")
print("Test message sent successfully!")

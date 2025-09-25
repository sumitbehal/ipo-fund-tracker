import os
from telegram import Bot

# Load secrets from environment variables
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

# Debug prints (optional, remove after testing)
print("Bot token:", bot_token)
print("Chat ID:", chat_id)

# Initialize bot
bot = Bot(token=bot_token)

# Send test message
bot.send_message(chat_id=chat_id, text="✅ Test message from your Telegram bot is working!")
print("Test message sent successfully!")

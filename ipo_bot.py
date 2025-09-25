import os
import asyncio
from telegram import Bot

bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

print("Bot token:", bot_token)
print("Chat ID:", chat_id)

async def main():
    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=chat_id, text="✅ Test message from your Telegram bot is working!")
    print("Message sent successfully!")

# Run the async function
asyncio.run(main())

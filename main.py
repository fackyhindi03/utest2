import asyncio
import logging

from telethon import TelegramClient
from config import API_ID, API_HASH, BOT_TOKEN
from handlers import register_handlers

logging.basicConfig(level=logging.INFO)

client = TelegramClient("hianime", API_ID, API_HASH)

async def main():
    await client.start(bot_token=BOT_TOKEN)
    await register_handlers(client)
    logging.info("🤖 Bot is up and running")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

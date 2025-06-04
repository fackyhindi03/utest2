import asyncio
import logging
import os

from telethon import TelegramClient
from telethon import __version__ as TELETHON_VERSION
from config import API_ID, API_HASH, BOT_TOKEN
from handlers import register_handlers

logging.basicConfig(level=logging.INFO)

async def _start_health_server():
    """
    A minimal HTTP server that always returns 200 OK. Render will detect
    this port as “open” and consider the service healthy.
    """
    port = int(os.environ.get("PORT", 8000))

    async def _handle(reader, writer):
        # Very basic HTTP/1.1 OK response (no body needed, just status)
        resp = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nOK"
        writer.write(resp)
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(_handle, "0.0.0.0", port)
    logging.info(f"🌐 Health‐check server listening on port {port}")
    return server

client = TelegramClient("hianime", API_ID, API_HASH)

async def main():
    await client.start(bot_token=BOT_TOKEN)
    await register_handlers(client)
    logging.info(f"🤖 Bot is up and running (Telethon v{TELETHON_VERSION})")

    # Start a tiny HTTP server so Render knows this process has bound to $PORT
    server = await _start_health_server()

    await client.run_until_disconnected()

    # When the bot disconnects, close the health‐check server as well:
    server.close()
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())

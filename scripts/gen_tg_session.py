"""
Генерация Telegram StringSession для Railway.
Запускай ОДИН РАЗ локально:
    cd backend && python ../scripts/gen_tg_session.py

Скопируй полученную строку в Railway → Variables → TELEGRAM_SESSION
"""
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 19512615
API_HASH = "4f98245b8d36ce15acf82a550cecdb0b"


async def main():
    async with TelegramClient(StringSession(), API_ID, API_HASH) as client:
        session_str = client.session.save()
        print("\n✅ Твоя сессия (скопируй в TELEGRAM_SESSION на Railway):\n")
        print(session_str)
        print()


if __name__ == "__main__":
    asyncio.run(main())

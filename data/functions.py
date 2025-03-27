import asyncio
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message
from data import bot


async def del_msg(message: Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except TelegramBadRequest:
        pass


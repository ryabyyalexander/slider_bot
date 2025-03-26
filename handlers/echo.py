from aiogram.types import Message
from aiogram import Router

from data import del_msg

router = Router()


@router.message()
async def send_echo(message: Message):
    try:
        await message.delete()
    except TypeError:
        await message.reply(text='Данный тип апдейтов не поддерживается методом send_copy')


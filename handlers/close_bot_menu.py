from aiogram import Router, Bot, F
from aiogram.types import Message

from data import del_msg

router = Router()


@router.message(F.text == '/close')
async def del_main_menu(message: Message, bot: Bot):
    await bot.delete_my_commands()
    msg = await message.answer(text='Кнопка "Menu" удалена')
    await message.delete()
    await del_msg(msg, 3)

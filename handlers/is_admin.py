from aiogram import Router, F
from aiogram.types import Message

from data import admin, del_msg, admins
from filters import IsAdmin

router = Router()


@router.message(F.text == '/admin', IsAdmin(admins))
async def func(message: Message):
    await message.delete()
    msg = await message.answer('is admin')
    await del_msg(msg, 4)


@router.message(F.text == '/admin', ~IsAdmin([int(admin)]))
async def func(message: Message):
    await message.delete()
    msg = await message.answer('is not admin')
    await del_msg(msg, 4)


# slider.py
import asyncio
from random import shuffle
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from data import bot, del_msg, admins, SPEED_OPTIONS, CYCLE_OPTIONS, CYCLE_DEFAULT
from data.functions import data_time
from filters import IsAdmin
from sql import data_users
from states.states import SlideShowState

router = Router()


async def get_photo_list():
    """Получает список фото из базы и перемешивает его"""
    photos = data_users.get_all_photos()
    if not photos:
        return None
    photo_list = [p[0] for p in photos]
    shuffle(photo_list)
    return photo_list


def get_keyboard(paused=False, expanded=False, index=0, total=0):
    control_buttons = [
        InlineKeyboardButton(text=f"{index + 1}/{total}", callback_data="info"),
        InlineKeyboardButton(text="+" if not expanded else '—', callback_data="toggle_expand"),
        InlineKeyboardButton(text="||" if not paused else "ᐅ", callback_data="pause" if not paused else "play"),
        InlineKeyboardButton(text='╳', callback_data='╳')
    ]
    cycle_buttons = [
        InlineKeyboardButton(text=str(cycle), callback_data=f"setcycle_{cycle}")
        for cycle in CYCLE_OPTIONS
    ]
    speed_buttons = [
        InlineKeyboardButton(text=f"{speed} сек", callback_data=f"setspeed_{speed}")
        for speed in SPEED_OPTIONS
    ]
    close_button = [
        InlineKeyboardButton(text="←", callback_data="prev"),
        InlineKeyboardButton(text="→", callback_data="next")]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[control_buttons])
    if expanded:
        keyboard.inline_keyboard.extend([cycle_buttons, speed_buttons, close_button])
    return keyboard


@router.callback_query(F.data == "toggle_expand")
async def toggle_expand(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    expanded = data.get("expanded", False)
    expanded = not expanded
    await state.update_data(expanded=expanded)
    await update_photo(callback.message.chat.id, data["msg_id"], data["index"], state,
                       paused=not data.get("playing", False), expanded=expanded)
    await callback.answer()


@router.message(F.text == "/start")
async def start_slideshow(message: Message, state: FSMContext):
    user_id = int(message.from_user.id)
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    user_name = message.from_user.username

    if not data_users.sql_get_user(user_id):
        is_admin = user_id in admins
        data_users.sql_new_user(user_id, first_name, last_name, user_name, is_admin)
        data_users.update_user_blocked(user_id, 0)
        await message.answer("🦆")
        await message.answer("Чи справжні «Надзвичайні крила»,чи це просто уява художника, залишається загадкою..")
        await message.delete()
    else:
        data_users.update_restart_count(user_id)
        data_users.update_user_blocked(user_id, 0)
        await message.delete()
        wellcome_msg = await message.answer(f"З поверненням, {first_name}!")
        await del_msg(wellcome_msg, 2)

    photo_list = await get_photo_list()
    if not photo_list:
        msg = await message.answer("❌ Немає доступних фотографій. Додайте фото.")
        await del_msg(msg, 5)
        return

    index = 0
    photo_id = photo_list[index]
    caption = f'{data_time()} \n'

    msg = await message.answer_photo(
        photo=photo_id,
        caption=caption,
        reply_markup=get_keyboard(expanded=False, index=index, total=len(photo_list))
    )

    await state.set_state(SlideShowState.viewing)
    await state.update_data(
        index=index,
        msg_id=msg.message_id,
        playing=True,
        cycle_count=0,
        cycle_length=CYCLE_DEFAULT,
        expanded=False,
        photo_list=photo_list,
        speed=3  # Добавлено значение по умолчанию для скорости
    )
    await asyncio.sleep(3)
    await asyncio.create_task(autoplay_slideshow(message.chat.id, state))


async def update_photo(chat_id: int, message_id: int, index: int, state: FSMContext, paused=False, expanded=False):
    data = await state.get_data()
    photo_list = data.get("photo_list", [])
    if not photo_list or index >= len(photo_list):
        return

    photo_id = photo_list[index]
    caption = f'{data_time()} \n'
    try:
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=InputMediaPhoto(media=photo_id, caption=caption),
            reply_markup=get_keyboard(paused, expanded, index, len(photo_list))
        )
    except TelegramBadRequest:
        pass


async def autoplay_slideshow(chat_id: int, state: FSMContext):
    while (await state.get_data()).get("playing", False):
        data = await state.get_data()
        photo_list = data.get("photo_list", [])
        if not photo_list:
            break

        current_index = data["index"]
        msg_id = data["msg_id"]
        cycle_count = data.get("cycle_count", 0)
        cycle_length = data.get("cycle_length", CYCLE_DEFAULT)
        speed = data.get("speed", 3)
        expanded = data.get("expanded", False)

        next_index = (current_index + 1) % len(photo_list)
        if cycle_count >= cycle_length - 1:
            await state.update_data(index=next_index, playing=False, cycle_count=0)
            await update_photo(chat_id, msg_id, next_index, state, paused=True, expanded=expanded)
            break
        else:
            await state.update_data(index=next_index, cycle_count=cycle_count + 1)
            await update_photo(chat_id, msg_id, next_index, state, expanded=expanded)
        await asyncio.sleep(speed)


@router.callback_query(F.data.in_(["prev", "next", "pause", "play"]))
async def slideshow_controls(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "index" not in data:
        msg = await callback.message.answer("❌ Слайдшоу ще не запущено.")
        await del_msg(msg, 2)
        return

    photo_list = data.get("photo_list", [])
    if not photo_list:
        return

    index = data["index"]
    msg_id = data["msg_id"]
    playing = data.get("playing", False)
    expanded = data.get("expanded", False)

    if callback.data == "prev":
        index = (index - 1) % len(photo_list)
        await state.update_data(index=index, cycle_count=0)
    elif callback.data == "next":
        index = (index + 1) % len(photo_list)
        await state.update_data(index=index, cycle_count=0)
    elif callback.data == "pause":
        await state.update_data(playing=False)
        await update_photo(callback.message.chat.id, msg_id, index, state, paused=True, expanded=expanded)
        await callback.answer("Слайдшоу призупинено.")
        return
    elif callback.data == "play":
        await state.update_data(playing=True, cycle_count=0)
        await update_photo(callback.message.chat.id, msg_id, index, state, paused=False, expanded=expanded)
        await asyncio.create_task(autoplay_slideshow(callback.message.chat.id, state))
        return

    await update_photo(callback.message.chat.id, msg_id, index, state, paused=not playing, expanded=expanded)
    await callback.answer()


@router.callback_query(F.data.startswith("setspeed_"))
async def set_speed(callback: CallbackQuery, state: FSMContext):
    try:
        new_speed = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("Неправильне значення швидкості.")
        return

    await state.update_data(speed=new_speed)
    msg = await callback.message.answer(f"Швидкість встановлена на {new_speed} сек.")
    await del_msg(msg, 2)

    data = await state.get_data()
    await update_photo(
        callback.message.chat.id,
        data["msg_id"],
        data["index"],
        state,  # Исправлено: передаем state вместо data["state"]
        paused=not data.get("playing", False),
        expanded=data.get("expanded", False)
    )


@router.callback_query(F.data.startswith("setcycle_"))
async def set_cycle_length(callback: CallbackQuery, state: FSMContext):
    try:
        new_cycle = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("Неправильне значення циклу.")
        return

    await state.update_data(cycle_length=new_cycle, cycle_count=0)
    msg = await callback.message.answer(f"Цикл встановлено на {new_cycle} фото.")
    await del_msg(msg, 2)

    data = await state.get_data()
    await update_photo(
        callback.message.chat.id,
        data["msg_id"],
        data["index"],
        state,  # Исправлено: передаем state вместо data["state"]
        paused=not data.get("playing", False),
        expanded=data.get("expanded", False)
    )


@router.callback_query(F.data.in_(['╳']))
async def process_sl(callback: CallbackQuery, state: FSMContext):
    await state.update_data(playing=False)
    try:
        if callback.message:
            first_name = callback.from_user.first_name
            msg = await callback.message.answer(f"До зустрічі, {first_name}!")
            await callback.message.delete()
            await del_msg(msg, 2)
    except TelegramBadRequest:
        await callback.answer("Повідомлення вже видалено або не знайдено.")
    await state.clear()

############################################################
###########################################################

@router.message(Command("addphoto"))
async def handle_add_photo_command(message: Message):
    if not message.photo:
        msg = await message.answer("❌ Будь ласка, відправте фото з підписом (необов'язково).")
        await del_msg(msg, 2)
        return

    if not data_users.sql_user_exists(message.from_user.id):
        msg = await message.answer("❌ Спочатку зареєструйтесь через /slider")
        await del_msg(msg, 2)
        return

    photo_id = message.photo[-1].file_id
    caption = message.caption

    try:
        data_users.add_photo(photo_id, message.from_user.id, caption)
        msg = await message.answer("✅ Фото успішно додано до бази!")
        await del_msg(msg, 2)
    except Exception as e:
        msg = await message.answer(f"❌ Помилка при додаванні фото: {e}")
        await del_msg(msg, 2)


@router.message(Command("myphotos"))
async def handle_my_photos(message: Message):
    photos = data_users.execute_query(
        "SELECT id, file_id FROM photos WHERE added_by = ?",
        (message.from_user.id,)
    ).fetchall()

    if not photos:
        await message.answer("❌ У вас немає доданих фото.")
        return

    for photo in photos:
        await message.answer_photo(
            photo[1],  # file_id
            caption=f"ID: {photo[0]}"  # id фото
        )

    await message.delete()


@router.message(Command('/deletephoto'), IsAdmin(admins))
async def handle_delete_photo(message: Message):
    try:
        photo_id = int(message.text.split()[1])
        data_users.delete_photo(photo_id)
        msg = await message.answer(f"✅ Фото {photo_id} видалено.")
        await del_msg(msg, 2)
        await message.delete()
    except (IndexError, ValueError):
        msg = await message.answer("❌ Використання: /deletephoto <ID>")
        await del_msg(msg, 2)
    except Exception as e:
        msg = await message.answer(f"❌ Помилка: {e}")
        await del_msg(msg, 2)


@router.message(Command("photostats"))
async def handle_photo_stats(message: Message):
    count = data_users.get_photo_count()
    msg = await message.answer(f"📊 У базі знаходиться {count} фотографій.")
    await del_msg(msg, 5)
    await message.delete()


@router.message(F.photo, IsAdmin(admins))
async def handle_any_photo(message: Message):
    if not data_users.sql_user_exists(message.from_user.id):
        msg = await message.answer("❌ Спочатку зареєструйтесь через /slider")
        await del_msg(msg, 2)
        return

    photo_id = message.photo[-1].file_id
    caption = message.caption

    try:
        data_users.add_photo(photo_id, message.from_user.id, caption)
        msg = await message.answer("✅ Фото успішно додано до бази!")
        await del_msg(msg, 2)
        await message.delete()
    except Exception as e:
        msg = await message.answer(f"❌ Помилка при додаванні фото: {e}")
        await del_msg(msg, 2)

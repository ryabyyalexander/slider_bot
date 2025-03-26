import asyncio
from random import shuffle
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from data import bot, del_msg, admins, SPEED_OPTIONS, CYCLE_OPTIONS, PHOTO_LIST, CYCLE_DEFAULT
from data.functions import data_time
from sql import data_users
from states.states import SlideShowState

router = Router()


def get_keyboard(paused=False, expanded=False):
    control_buttons = [
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
    await update_photo(callback.message.chat.id, data["msg_id"], data["index"], paused=not data.get("playing", False),
                       expanded=expanded)
    await callback.answer()


@router.message(F.text == "/slider")
async def start_slideshow(message: Message, state: FSMContext):
    user_id = int(message.from_user.id)
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    user_name = message.from_user.username

    # Проверяем, существует ли пользователь в базе данных
    if not data_users.sql_get_user(user_id):
        # Если пользователя нет, регистрируем его
        is_admin = user_id in admins  # Проверяем, является ли пользователь администратором
        data_users.sql_new_user(user_id, first_name, last_name, user_name, is_admin)
        # Обновляем статус "блокировки" на 0
        data_users.update_user_blocked(user_id, 0)
        # Получаем количество перезапусков (для нового пользователя это будет 0)
        await message.answer("🦆")
        await message.answer("Чи справжні «Надзвичайні крила»,чи це просто уява художника, залишається загадкою..")
        await message.delete()
        # Отправляем случайный стикер
        # sticker_msg = await message.answer_sticker(choice(stickers))
    else:
        # Если пользователь уже существует, увеличиваем счётчик перезапусков
        data_users.update_restart_count(user_id)  # Увеличиваем restart_count
        # обновляем статус "блокировки" на 0
        data_users.update_user_blocked(user_id, 0)
        await message.delete()
        # Отправляем случайный стикер
        # sticker_msg = await message.answer_sticker(choice(stickers))
        wellcome_msg = await message.answer(f"З поверненням, {first_name}!")
        await del_msg(wellcome_msg, 2)

    # Продолжаем запуск слайд-шоу
    if not PHOTO_LIST:
        msg = await message.answer("❌ Немає доступних фотографій для слайдшоу.")
        await del_msg(msg, 2)
        return

    shuffle(PHOTO_LIST)
    index = 0
    photo_id = PHOTO_LIST[index]
    caption = f'{data_time()} \n'

    msg = await message.answer_photo(photo=photo_id, caption=caption, reply_markup=get_keyboard(expanded=False))

    # await del_msg(sticker_msg, 2)
    await state.set_state(SlideShowState.viewing)
    await state.update_data(index=index, msg_id=msg.message_id, playing=True, cycle_count=0, cycle_length=CYCLE_DEFAULT,
                            expanded=False)
    await asyncio.sleep(3)
    await asyncio.create_task(autoplay_slideshow(message.chat.id, state))


async def update_photo(chat_id: int, message_id: int, index: int, paused=False, expanded=False):
    photo_id = PHOTO_LIST[index]
    caption = f'{data_time()} \n'
    try:
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=InputMediaPhoto(media=photo_id, caption=caption),
            reply_markup=get_keyboard(paused, expanded)
        )
    except TelegramBadRequest:
        pass


async def autoplay_slideshow(chat_id: int, state: FSMContext):
    while (await state.get_data()).get("playing", False):
        data = await state.get_data()
        current_index = data["index"]
        msg_id = data["msg_id"]
        cycle_count = data.get("cycle_count", 0)
        cycle_length = data.get("cycle_length", CYCLE_DEFAULT)
        speed = data.get("speed", 3)
        expanded = data.get("expanded", False)
        next_index = (current_index + 1) % len(PHOTO_LIST)
        if cycle_count >= cycle_length - 1:
            await state.update_data(index=next_index, playing=False, cycle_count=0)
            await update_photo(chat_id, msg_id, next_index, paused=True, expanded=expanded)
            break
        else:
            await state.update_data(index=next_index, cycle_count=cycle_count + 1)
            await update_photo(chat_id, msg_id, next_index, expanded=expanded)
        await asyncio.sleep(speed)


@router.callback_query(F.data.in_(["prev", "next", "pause", "play"]))
async def slideshow_controls(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "index" not in data:
        msg = await callback.message.answer("❌ Слайдшоу ще не запущено.")
        await del_msg(msg, 2)
        return
    index = data["index"]
    msg_id = data["msg_id"]
    playing = data.get("playing", False)
    expanded = data.get("expanded", False)
    if callback.data == "prev":
        index = (index - 1) % len(PHOTO_LIST)
        await state.update_data(index=index, cycle_count=0)
    elif callback.data == "next":
        index = (index + 1) % len(PHOTO_LIST)
        await state.update_data(index=index, cycle_count=0)
    elif callback.data == "pause":
        await state.update_data(playing=False)
        await update_photo(callback.message.chat.id, msg_id, index, paused=True, expanded=expanded)
        await callback.answer("Слайдшоу призупинено.")
        return
    elif callback.data == "play":
        await state.update_data(playing=True, cycle_count=0)
        await update_photo(callback.message.chat.id, msg_id, index, paused=False, expanded=expanded)
        await asyncio.create_task(autoplay_slideshow(callback.message.chat.id, state))
        return
    await update_photo(callback.message.chat.id, msg_id, index, paused=not playing, expanded=expanded)
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
    chat_id = callback.message.chat.id
    msg_id = data["msg_id"]
    index = data["index"]
    playing = data.get("playing", False)
    expanded = data.get("expanded", False)
    await update_photo(chat_id, msg_id, index, paused=not playing, expanded=expanded)


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
    chat_id = callback.message.chat.id
    msg_id = data["msg_id"]
    index = data["index"]
    playing = data.get("playing", False)
    expanded = data.get("expanded", False)
    await update_photo(chat_id, msg_id, index, paused=not playing, expanded=expanded)


@router.callback_query(F.data.in_(['╳']))
async def process_sl(callback: CallbackQuery, state: FSMContext):
    await state.update_data(playing=False)
    try:
        if callback.message:
            # Получаем имя пользователя
            first_name = callback.from_user.first_name
            # Отправляем сообщение с прощанием
            msg = await callback.message.answer(f"До зустрічі, {first_name}!")
            # Удаляем сообщение со слайд-шоу
            await callback.message.delete()
            await del_msg(msg, 2)

    except TelegramBadRequest:
        await callback.answer("Повідомлення вже видалено або не знайдено.")
    await state.clear()

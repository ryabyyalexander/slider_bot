# "Рефакторинг слайд-шоу: разделение на модули"
import asyncio
from random import shuffle, choice
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from data import bot, del_msg, admins, CYCLE_DEFAULT, stickers
from filters import IsAdmin
from sql import data_base
from states.states import SlideShowState

router = Router()


async def get_photo_list():
    """Получает список фото из базы и перемешивает его"""
    photos = data_base.get_all_photos()
    if not photos:
        return None
    photo_list = [p[0] for p in photos]
    shuffle(photo_list)
    return photo_list


def get_keyboard(paused=False, expanded=False, index=0, total=0):
    control_buttons = [
        InlineKeyboardButton(text="||" if not paused else "ᐅ", callback_data="pause" if not paused else "play")
    ]
    arrow_button = [
        InlineKeyboardButton(text=f"{index + 1}/{total}", callback_data="info"),
        InlineKeyboardButton(text="←", callback_data="prev"),
        InlineKeyboardButton(text="→", callback_data="next"),
        InlineKeyboardButton(text='╳', callback_data='╳')
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[control_buttons])
    if expanded or paused:  # Показываем дополнительные кнопки когда expanded=True или paused=True
        keyboard.inline_keyboard.extend([arrow_button])
    return keyboard


@router.message(F.text == "/start")
async def start_slideshow(message: Message, state: FSMContext):
    user_id = int(message.from_user.id)
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    user_name = message.from_user.username

    if not data_base.sql_get_user(user_id):
        is_admin = user_id in admins
        data_base.sql_new_user(user_id, first_name, last_name, user_name, is_admin)
        data_base.update_user_blocked(user_id, 0)
        msg = await message.answer("Якщо думаєш, що все зрозуміло - почекай пару секунд.")
        await message.delete()
        await del_msg(msg, 4)
        await message.answer("Ти не побачиш тут шаблонів. Ти готовий?")
    else:
        data_base.update_restart_count(user_id)
        data_base.update_user_blocked(user_id, 0)
        await message.delete()
        wellcome_msg = await message.answer(f"Стартуемо, {first_name}!")
        await asyncio.gather(
            del_msg(wellcome_msg, 3)
        )

    photo_list = await get_photo_list()
    if not photo_list:
        msg = await message.answer("❌ Немає доступних фотографій. Додайте фото.")
        await del_msg(msg, 5)
        return

    index = 0
    photo_id = photo_list[index]

    msg = await message.answer_photo(
        photo=photo_id,
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
        speed=3,
        first_photo_shown=True
    )

    await asyncio.sleep(2)
    await update_photo(message.chat.id, msg.message_id, index, state)
    await asyncio.create_task(autoplay_slideshow(message.chat.id, state))


async def update_photo(chat_id: int, message_id: int, index: int, state: FSMContext, paused=False, expanded=False):
    data = await state.get_data()
    photo_list = data.get("photo_list", [])
    if not photo_list or index >= len(photo_list):
        return

    photo_id = photo_list[index]

    try:
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=InputMediaPhoto(media=photo_id),
            reply_markup=get_keyboard(paused, expanded, index, len(photo_list))
        )
    except TelegramBadRequest:
        pass


async def autoplay_slideshow(chat_id: int, state: FSMContext):
    data = await state.get_data()
    if data.get("first_photo_shown", False):
        await state.update_data(first_photo_shown=False)
        await asyncio.sleep(data.get("speed", 3))

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
    # Получаем текущее состояние
    data = await state.get_data()

    # Если состояние пустое или слайд-шоу не запущено
    if not data or "index" not in data or "photo_list" not in data:
        try:
            if callback.message:
                first_name = callback.from_user.first_name
                # Получаем количество фото из базы данных
                # quont = data_base.get_photo_count()
                msg = await callback.message.answer(
                    f"Дякуемо за прибирання!\n{first_name}, можете перезапусти слайдер!"
                )
                await callback.message.delete()
                await del_msg(msg, 5)
        except TelegramBadRequest:
            await callback.answer("Повідомлення вже видалено або не знайдено.")
        await state.clear()
        return

    # Остальная часть обработчика остается без изменений
    photo_list = data.get("photo_list", [])
    if not photo_list:
        msg = await callback.message.answer("❌ Немає доступних фотографій.")
        await del_msg(msg, 2)
        return

    index = data["index"]
    msg_id = data["msg_id"]
    playing = data.get("playing", False)

    if callback.data == "prev":
        index = (index - 1) % len(photo_list)
        await state.update_data(index=index, cycle_count=0)
    elif callback.data == "next":
        index = (index + 1) % len(photo_list)
        await state.update_data(index=index, cycle_count=0)
    elif callback.data == "pause":
        await state.update_data(playing=False, expanded=True)
        await update_photo(callback.message.chat.id, msg_id, index, state, paused=True, expanded=True)
        await callback.answer("Слайдшоу призупинено.")
        return
    elif callback.data == "play":
        await state.update_data(playing=True, expanded=False)
        await update_photo(callback.message.chat.id, msg_id, index, state, paused=False, expanded=False)
        await asyncio.create_task(autoplay_slideshow(callback.message.chat.id, state))
        await callback.answer("Слайдшоу продовжено.")
        return

    await update_photo(callback.message.chat.id, msg_id, index, state, paused=not playing,
                       expanded=data.get("expanded", False))
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


@router.message(Command("myphotos"))
async def handle_my_photos(message: Message):
    photos = data_base.execute_query(
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


@router.message(Command("del"), IsAdmin(admins))
async def handle_delete_photo(message: Message):
    try:
        # Проверяем, что передан аргумент с ID фото
        if len(message.text.split()) < 2:
            msg = await message.answer("❌ Використання: /del <ID>")
            await del_msg(msg, 2)
            return

        photo_id = int(message.text.split()[1])
        # print(f'Пытаемся удалить фото с ID: {photo_id}')   Логирование ID

        # Проверяем существование фото перед удалением
        photo_exists = data_base.execute_query(
            "SELECT 1 FROM photos WHERE id = ?",
            (photo_id,)
        ).fetchone()

        if not photo_exists:
            msg = await message.answer(f"❌ Фото з ID {photo_id} не знайдено.")
            await del_msg(msg, 2)
            return

        # Удаляем фото
        deleted = data_base.delete_photo(photo_id)
        # print(f'Результат удаления: {deleted}')   Логирование результата

        if deleted:
            msg = await message.answer(f"✅ Фото {photo_id} успішно видалено.")
        else:
            msg = await message.answer(f"❌ Не вдалося видалити фото {photo_id}.")

        await del_msg(msg, 2)
        await message.delete()

    except ValueError:
        msg = await message.answer("❌ ID фото має бути числом.")
        await del_msg(msg, 2)
    except Exception as e:
        print(f'Ошибка при удалении фото: {str(e)}')  # Логирование ошибки
        msg = await message.answer(f"❌ Помилка: {str(e)}")
        await del_msg(msg, 2)


@router.message(Command("photostats"))
async def handle_photo_stats(message: Message):
    count = data_base.get_photo_count()
    msg = await message.answer(f"📊 У базі знаходиться {count} фотографій.")
    await del_msg(msg, 5)
    await message.delete()


@router.message(F.photo, IsAdmin(admins))
async def handle_any_photo(message: Message):
    photo_id = message.photo[-1].file_id
    caption = message.caption

    try:
        data_base.add_photo(photo_id, message.from_user.id, caption)
        msg = await message.answer("✅ Фото успішно додано до бази!")
        await del_msg(msg, 2)
        await message.delete()
    except Exception as e:
        msg = await message.answer(f"❌ Помилка при додаванні фото: {e}")
        await del_msg(msg, 2)


@router.callback_query(F.data.in_(['╳']))
async def process_sl(callback: CallbackQuery, state: FSMContext):
    await state.update_data(playing=False)
    try:
        if callback.message:
            first_name = callback.from_user.first_name
            msg = await callback.message.answer(f"Дякую за увагу, {first_name}!")
            await callback.message.delete()
            await del_msg(msg, 2)
    except TelegramBadRequest:
        await callback.answer("Повідомлення вже видалено або не знайдено.")
    await state.clear()

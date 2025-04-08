import asyncio
from random import shuffle
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from data import bot, del_msg, admins, CYCLE_DEFAULT
from data.lexicon import start_message
from filters import IsAdmin
from keyboards import get_keyboard
from sql import data_base
from states.states import SlideShowState

router = Router()


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
        await message.answer(start_message)
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
        msg = await message.answer("Додайте перше фото. Будьте першим.")
        await del_msg(msg, 5)
        return

    index = 0
    photo_id = photo_list[index]

    msg = await message.answer_photo(
        photo=photo_id,
        reply_markup=get_keyboard(expanded=False, index=index, total=len(photo_list), user_id=user_id)
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
    await update_photo(message.chat.id, msg.message_id, index, state, user_id=user_id)
    await asyncio.create_task(autoplay_slideshow(message.chat.id, state))


@router.callback_query(F.data.in_(["prev", "next", "pause", "play"]))
async def slideshow_controls(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if not data or "index" not in data or "photo_list" not in data:
        try:
            if callback.message:
                first_name = callback.from_user.first_name
                msg = await callback.message.answer(
                    f"Дякуемо за чистоту!\n{first_name}, зараз можете перезапусти слайдер!"
                )
                await callback.message.delete()
                await del_msg(msg, 5)
        except TelegramBadRequest:
            await callback.answer("Повідомлення вже видалено або не знайдено.")
        await state.clear()
        return

    photo_list = data.get("photo_list", [])
    if not photo_list:
        msg = await callback.message.answer("❌ Немає доступних фотографій.")
        await del_msg(msg, 2)
        return

    index = data["index"]
    msg_id = data["msg_id"]
    playing = data.get("playing", False)
    user_id = callback.from_user.id

    if callback.data == "prev":
        index = (index - 1) % len(photo_list)
        await state.update_data(index=index, cycle_count=0)
    elif callback.data == "next":
        index = (index + 1) % len(photo_list)
        await state.update_data(index=index, cycle_count=0)
    elif callback.data == "pause":
        await state.update_data(playing=False, expanded=True)
        await update_photo(callback.message.chat.id, msg_id, index, state, paused=True, expanded=True, user_id=user_id)
        await callback.answer("Слайдшоу призупинено.")
        return
    elif callback.data == "play":
        await state.update_data(playing=True, expanded=False)
        await update_photo(callback.message.chat.id, msg_id, index, state, paused=False, expanded=False,
                           user_id=user_id)
        await asyncio.create_task(autoplay_slideshow(callback.message.chat.id, state))
        return

    await update_photo(callback.message.chat.id, msg_id, index, state, paused=not playing,
                       expanded=data.get("expanded", False), user_id=user_id)
    await callback.answer()


@router.callback_query(F.data == "delete_photo", IsAdmin(admins))
async def delete_current_photo(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data or "photo_list" not in data or "index" not in data:
        await callback.answer("❌ Невозможно удалить фото: состояние не найдено.")
        return

    photo_list = data["photo_list"]
    index = data["index"]
    if index >= len(photo_list):
        await callback.answer("❌ Невозможно удалить фото: неверный индекс.")
        return

    file_id = photo_list[index]

    try:
        # Сначала получаем ID фото по file_id
        cursor = data_base.execute_query(
            "SELECT id FROM photos WHERE file_id = ?",
            (file_id,)
        )
        photo_record = cursor.fetchone()

        if not photo_record:
            await callback.answer("❌ Фото не найдено в базе данных.")
            return

        photo_id = photo_record[0]
        deleted = data_base.delete_photo(photo_id)

        if deleted:
            new_photo_list = await get_photo_list()
            if not new_photo_list:
                await callback.message.delete()
                msg = await callback.message.answer("❌ База фото пуста. Добавьте новые фото.")
                await del_msg(msg, 3)
                await state.clear()
                return

            new_index = min(index, len(new_photo_list) - 1)

            await state.update_data(
                photo_list=new_photo_list,
                index=new_index,
                cycle_count=0
            )

            await update_photo(
                callback.message.chat.id,
                callback.message.message_id,
                new_index,
                state,
                paused=data.get("playing", False),
                expanded=data.get("expanded", False),
                user_id=callback.from_user.id
            )
            await callback.answer("✅ Фото успешно удалено.")
        else:
            await callback.answer("❌ Не удалось удалить фото.")
    except Exception as e:
        print(f"Ошибка при удалении фото: {e}")
        await callback.answer(f"❌ Ошибка при удалении фото: {e}")


@router.message(F.photo, IsAdmin(admins))  # , IsAdmin(admins)
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


async def get_photo_list():
    """Получает список фото из базы и перемешивает его"""
    photos = data_base.get_all_photos()
    if not photos:
        return None
    photo_list = [p[0] for p in photos]
    shuffle(photo_list)
    return photo_list


async def update_photo(chat_id: int, message_id: int, index: int, state: FSMContext, paused=False, expanded=False,
                       user_id=None):
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
            reply_markup=get_keyboard(paused, expanded, index, len(photo_list), user_id)
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
        user_id = data.get("user_id", None)

        next_index = (current_index + 1) % len(photo_list)
        if cycle_count >= cycle_length - 1:
            await state.update_data(index=next_index, playing=False, cycle_count=0)
            await update_photo(chat_id, msg_id, next_index, state, paused=True, expanded=expanded, user_id=user_id)
            break
        else:
            await state.update_data(index=next_index, cycle_count=cycle_count + 1)
            await update_photo(chat_id, msg_id, next_index, state, expanded=expanded, user_id=user_id)
        await asyncio.sleep(speed)

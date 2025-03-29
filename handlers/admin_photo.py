
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from data import del_msg, admins
from filters import IsAdmin
from sql import data_base

router = Router()


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

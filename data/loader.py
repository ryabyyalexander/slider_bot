import asyncio
from aiogram import Bot, Dispatcher
# import logging
from aiogram.fsm.storage.memory import MemoryStorage
from data.config import Config, load_config, admin

storage = MemoryStorage()

# logging.basicConfig(
#     level=logging.INFO,
#     format='%(filename)s:%(lineno)d #%(levelname)-8s '
#            '[%(asctime)s] - %(name)s - %(message)s',
#     handlers=[
#         # logging.FileHandler("bot.log"),  # Запись логов в файл
#         logging.StreamHandler()  # Вывод логов в консоль
#     ]
# )

# logger = logging.getLogger(__name__)
#
# # Пример использования логера
# logger.info("Программа запущена")
# logger.warning("Это предупреждение")
# logger.error("Произошла ошибка")

config: Config = load_config()
bot = Bot(token=config.tg_bot.token, parse_mode='HTML')
dp = Dispatcher(storage=storage)


async def on_startup():
    print('bot online')
    msg = await bot.send_message(admin, 'bot online')
    await asyncio.sleep(5)
    await msg.delete()

    # asyncio.create_task(keep_alive(bot))


async def on_shutdown():
    print('bot closed')
    await storage.close()
    msg = await bot.send_message(admin, 'bot closed')
    await asyncio.sleep(5)
    await msg.delete()


async def keep_alive(bott: Bot):
    while True:
        try:
            await bott.get_me()  # Простое обращение к Telegram API
            print('обращение к Telegram API')
        except Exception as e:
            print(f"Keep-alive error: {e}")
        await asyncio.sleep(300)  # Запрос каждые 5 минут

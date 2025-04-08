from handlers import (close_bot_menu, echo, user_block_bot, slider_illia, admin_photo)

if __name__ == "__main__":
    from data.loader import dp, bot, on_startup, on_shutdown

    from keyboards import set_main_menu

    dp.startup.register(set_main_menu)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    dp.include_router(router=user_block_bot.router)
    dp.include_router(router=close_bot_menu.router)
    dp.include_router(router=slider_illia.router)
    dp.include_router(router=admin_photo.router)
    dp.include_router(router=echo.router)

    dp.run_polling(bot)

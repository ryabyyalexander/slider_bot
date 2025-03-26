from aiogram.types import BotCommand

from data import MENU_COMMANDS, bot


async def set_main_menu():
    main_menu_commands = [
        BotCommand(command=command, description=description)
        for command, description in MENU_COMMANDS.items()]
    await bot.set_my_commands(main_menu_commands)

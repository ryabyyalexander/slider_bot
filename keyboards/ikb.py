from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from data import SPEED_OPTIONS, CYCLE_OPTIONS


def get_keyboard(paused=False, expanded=False, index=0, total=0):
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
        keyboard.inline_keyboard.extend([close_button])
    return keyboard
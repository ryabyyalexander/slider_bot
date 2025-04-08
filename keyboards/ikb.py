from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


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

from aiogram.fsm.state import State, StatesGroup


class State_load_product(StatesGroup):
    load_photo = State()
    load_content = State()


class State_add_photo(StatesGroup):
    start = State()
    close = State()


class State_add_product_params(StatesGroup):
    name = State()
    price = State()
    category = State()
    brand = State()


class SlideShowState(StatesGroup):
    viewing = State()

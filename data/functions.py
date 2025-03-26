import asyncio
from datetime import datetime
from random import shuffle

import requests
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message
from data import bot
from sql import data_users


async def del_msg(message: Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except TelegramBadRequest:
        pass


# Словари для названий месяцев и дней недели
months = {
    1: "січня", 2: "лютого", 3: "березня", 4: "квітня",
    5: "травня", 6: "червня", 7: "липня", 8: "серпня",
    9: "вересня", 10: "жовтня", 11: "листопада", 12: "грудня"
}

days_of_week = {
    0: "понеділок", 1: "вівторок", 2: "середа",
    3: "четвер", 4: "п’ятниця", 5: "субота", 6: "неділя"
}


# Получение текущей даты


def data_time():
    now = datetime.now()
    # Форматирование даты
    day = now.day
    month = months[now.month]
    day_of_week = days_of_week[now.weekday()]
    year = now.year

    return f"{day} {month} {year}, {day_of_week}"


def get_euro_exchange_rate():
    url = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=EUR&json"
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception("Не удалось получить данные с сайта НБУ")

    data = response.json()

    if not data or 'rate' not in data[0]:
        raise Exception("Не удалось найти курс евро")

    return data[0]['rate']

def get_usd_exchange_rate():
    url = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json"
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception("Не удалось получить данные с сайта НБУ")

    data = response.json()

    if not data or 'rate' not in data[0]:
        raise Exception("Не удалось найти курс доллара")

    return data[0]['rate']


async def get_photo_list():
    """Получает список фото из базы и перемешивает его"""
    photos = data_users.get_all_photos()
    if not photos:
        return None
    photo_list = [p[0] for p in photos]
    shuffle(photo_list)
    return photo_list
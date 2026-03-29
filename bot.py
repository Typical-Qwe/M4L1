from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logic import *
import threading
import time
import os
import cv2
from config import *

bot = TeleBot(API_TOKEN)

SEND_INTERVAL = 60


def gen_markup(id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Получить!", callback_data=id))
    return markup


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    prize_id = call.data
    user_id = call.message.chat.id

    if manager.get_winners_count(prize_id) < 3:
        if manager.add_winner(user_id, prize_id):
            img = manager.get_prize_img(prize_id)
            with open(f'img/{img}', 'rb') as photo:
                bot.send_photo(user_id, photo, caption="Ты выиграл! +10 монет 💰")
        else:
            bot.send_message(user_id, "Ты уже получил это")
    else:
        bot.send_message(user_id, "Не успел 😢")


def send_message():
    prize_id, img = manager.get_random_prize()[:2]
    manager.mark_prize_used(prize_id)
    hide_img(img)

    for user in manager.get_users():
        with open(f'hidden_img/{img}', 'rb') as photo:
            bot.send_photo(user, photo, reply_markup=gen_markup(prize_id))


def scheduler():
    while True:
        send_message()
        time.sleep(SEND_INTERVAL)


@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.id not in manager.get_users():
        manager.add_user(message.chat.id, message.from_user.username)
        bot.send_message(message.chat.id, "Ты зарегистрирован!")


@bot.message_handler(commands=['balance'])
def balance(message):
    coins = manager.get_coins(message.chat.id)
    bot.send_message(message.chat.id, f"💰 {coins} монет")


@bot.message_handler(commands=['retry'])
def retry(message):
    user_id = message.chat.id

    if not manager.spend_coins(user_id, 5):
        bot.send_message(user_id, "Нужно 5 монет")
        return

    import random
    lost = manager.get_lost_prizes(user_id)

    if not lost:
        bot.send_message(user_id, "У тебя всё есть")
        return

    img = random.choice(lost)[0]

    with open(f'img/{img}', 'rb') as photo:
        bot.send_photo(user_id, photo, caption="🎁 Бонус!")


@bot.message_handler(commands=['my_score'])
def my_score(message):
    user_id = message.chat.id
    info = manager.get_winners_img(user_id)

    if not info:
        bot.send_message(user_id, "Нет призов")
        return

    prizes = [x[0] for x in info]

    paths = os.listdir('img')
    paths = [f'img/{x}' if x in prizes else f'hidden_img/{x}' for x in paths]

    collage = create_collage(paths)

    path = f'collage_{user_id}.jpg'
    cv2.imwrite(path, collage)

    with open(path, 'rb') as photo:
        bot.send_photo(user_id, photo)


@bot.message_handler(commands=['set_interval'])
def set_interval(message):
    global SEND_INTERVAL
    if message.chat.id == ADMIN_ID:
        SEND_INTERVAL = int(message.text.split()[1])
        bot.send_message(message.chat.id, "Интервал обновлён")


def polling():
    bot.polling(none_stop=True)


if __name__ == '__main__':
    manager = DatabaseManager(DATABASE)
    manager.create_tables()

    t1 = threading.Thread(target=polling)
    t2 = threading.Thread(target=scheduler)

    t1.start()
    t2.start()
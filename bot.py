from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logic import *
import schedule
import threading
import time
from config import *
import cv2
import os

bot = TeleBot(API_TOKEN)


def gen_markup(id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("Получить!", callback_data=id))
    return markup


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    prize_id = call.data
    user_id = call.message.chat.id

    if manager.get_winners_count(prize_id) < 3:
        res = manager.add_winner(user_id, prize_id)

        if res:
            img = manager.get_prize_img(prize_id)
            with open(f'img/{img}', 'rb') as photo:
                bot.send_photo(user_id, photo, caption="Ты выиграл!")
        else:
            bot.send_message(user_id, "Ты уже получил этот приз!")
    else:
        bot.send_message(user_id, "Ты не успел 😢")


def send_message():
    prize_id, img = manager.get_random_prize()[:2]
    manager.mark_prize_used(prize_id)
    hide_img(img)

    for user in manager.get_users():
        with open(f'hidden_img/{img}', 'rb') as photo:
            bot.send_photo(user, photo, reply_markup=gen_markup(prize_id))


def shedule_thread():
    schedule.every(1).minutes.do(send_message)

    while True:
        schedule.run_pending()
        time.sleep(1)


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id

    if user_id in manager.get_users():
        bot.send_message(user_id, "Ты уже зарегистрирован")
    else:
        manager.add_user(user_id, message.from_user.username)
        bot.send_message(user_id, "Ты зарегистрирован!")


@bot.message_handler(commands=['rating'])
def rating(message):
    res = manager.get_rating()
    text = "\n".join([f"{x[0]} — {x[1]}" for x in res])
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['my_score'])
def get_my_score(message):
    user_id = message.chat.id

    info = manager.get_winners_img(user_id)

    if not info:
        bot.send_message(user_id, "У тебя пока нет призов")
        return

    prizes = [x[0] for x in info]

    image_paths = os.listdir('img')
    image_paths = [
        f'img/{x}' if x in prizes else f'hidden_img/{x}'
        for x in image_paths
    ]

    collage = create_collage(image_paths)

    if collage is None:
        bot.send_message(user_id, "Ошибка коллажа")
        return

    path = f'collage_{user_id}.jpg'
    cv2.imwrite(path, collage)

    with open(path, 'rb') as photo:
        bot.send_photo(user_id, photo)


def polling():
    bot.polling(none_stop=True)


if __name__ == '__main__':
    manager = DatabaseManager(DATABASE)
    manager.create_tables()

    t1 = threading.Thread(target=polling)
    t2 = threading.Thread(target=shedule_thread)

    t1.start()
    t2.start()
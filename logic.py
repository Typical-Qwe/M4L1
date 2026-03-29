import sqlite3
from datetime import datetime
from config import DATABASE
import os
import cv2
import numpy as np
from math import sqrt, ceil, floor


class DatabaseManager:
    def __init__(self, database):
        self.database = database

    def create_tables(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                user_name TEXT,
                coins INTEGER DEFAULT 0
            )
            ''')

            conn.execute('''
            CREATE TABLE IF NOT EXISTS prizes (
                prize_id INTEGER PRIMARY KEY,
                image TEXT,
                used INTEGER DEFAULT 0
            )
            ''')

            conn.execute('''
            CREATE TABLE IF NOT EXISTS winners (
                user_id INTEGER,
                prize_id INTEGER,
                win_time TEXT
            )
            ''')

    def add_user(self, user_id, user_name):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute(
                'INSERT INTO users (user_id, user_name) VALUES (?, ?)',
                (user_id, user_name)
            )

    def add_prize(self, data):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.executemany(
                'INSERT INTO prizes (image) VALUES (?)',
                data
            )

    def add_winner(self, user_id, prize_id):
        win_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM winners WHERE user_id=? AND prize_id=?",
                (user_id, prize_id)
            )

            if cur.fetchall():
                return 0
            else:
                conn.execute(
                    "INSERT INTO winners VALUES (?, ?, ?)",
                    (user_id, prize_id, win_time)
                )
                self.add_coins(user_id, 10)
                return 1

    def add_coins(self, user_id, amount):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute(
                "UPDATE users SET coins = coins + ? WHERE user_id = ?",
                (amount, user_id)
            )

    def get_coins(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT coins FROM users WHERE user_id=?", (user_id,))
            return cur.fetchone()[0]

    def spend_coins(self, user_id, amount):
        coins = self.get_coins(user_id)
        if coins >= amount:
            self.add_coins(user_id, -amount)
            return True
        return False

    def get_lost_prizes(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT image FROM prizes
                WHERE prize_id NOT IN (
                    SELECT prize_id FROM winners WHERE user_id = ?
                )
            ''', (user_id,))
            return cur.fetchall()

    def get_users(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM users")
            return [x[0] for x in cur.fetchall()]

    def get_prize_img(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT image FROM prizes WHERE prize_id=?", (prize_id,))
            return cur.fetchone()[0]

    def get_random_prize(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM prizes WHERE used=0 ORDER BY RANDOM()")
            return cur.fetchone()

    def mark_prize_used(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute("UPDATE prizes SET used=1 WHERE prize_id=?", (prize_id,))

    def get_winners_count(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM winners WHERE prize_id=?", (prize_id,))
            return cur.fetchone()[0]

    def get_winners_img(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT image FROM winners
                INNER JOIN prizes ON winners.prize_id = prizes.prize_id
                WHERE user_id = ?
            ''', (user_id,))
            return cur.fetchall()


def hide_img(img_name):
    image = cv2.imread(f'img/{img_name}')
    blurred = cv2.GaussianBlur(image, (15, 15), 0)
    small = cv2.resize(blurred, (30, 30))
    pixel = cv2.resize(small, (image.shape[1], image.shape[0]))
    cv2.imwrite(f'hidden_img/{img_name}', pixel)


def create_collage(image_paths):
    images = []

    for path in image_paths:
        img = cv2.imread(path)
        if img is not None:
            images.append(img)

    if not images:
        return None

    num_images = len(images)
    num_cols = max(1, floor(sqrt(num_images)))
    num_rows = ceil(num_images / num_cols)

    h, w = images[0].shape[:2]
    collage = np.zeros((num_rows * h, num_cols * w, 3), dtype=np.uint8)

    for i, img in enumerate(images):
        row = i // num_cols
        col = i % num_cols
        collage[row*h:(row+1)*h, col*w:(col+1)*w] = img

    return collage
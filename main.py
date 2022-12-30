import time
import re
import datetime
import threading
import multiprocessing

import telebot
import yandex_music
from telebot import types
from yandex_music import Client

from config import *
from user_input import parse_url, try_get_url
from dbhelper import DBCursor, track_in_db, add_track_db, get_all_tracks_db, get_cursor
from statistics import create_box_plot, most_popular_artist
import statistics


BOT_INTERVAL = 3
BOT_TIMEOUT = 60


bot = None
client = Client(YAM_TOKEN)
client.init()
cursor, db_connection = get_cursor()
ctx = multiprocessing.get_context('spawn')


def get_playlist_kind(client):
    for playlist in client.usersPlaylistsList():
        if playlist['title'] == 'Туса 2.0':
            return playlist['kind']
    raise NotImplemented


def get_playlist_revision(client):
    for playlist in client.usersPlaylistsList():
        if playlist['title'] == 'Туса 2.0':
            return playlist['revision']
    raise NotImplemented


def in_playlist(client, playlist_kind, track_id):
    for track in client.usersPlaylists(kind=playlist_kind)['tracks']:
        if track['track']['id'] == track_id:
            return True
    return False


def get_artists_and_name(client, track_id):
    track = client.tracks(track_id)
    name = track[0]['title']
    artists = []
    for artist in track[0]['artists']:
        a = client.artists(artist['id'])
        artists.append(a[0]['name'])
    return name, artists


def get_all_tracks(client):
    playlist = client.usersPlaylists(kind=get_playlist_kind(client))
    all_tracks = []
    for track in playlist['tracks']:
        all_tracks.append(get_artists_and_name(client, track['id']))
    return all_tracks


spams = {}
msgs = 4 # Messages in
max = 5 # Seconds
ban = 5 # Seconds
def is_spam(user_id):
    try:
        usr = spams[user_id]
        usr["messages"] += 1
    except:
        spams[user_id] = {"next_time": int(time.time()) + max, "messages": 1, "banned": 0}
        usr = spams[user_id]
    if usr["banned"] >= int(time.time()):
        return True
    else:
        if usr["next_time"] >= int(time.time()):
            if usr["messages"] >= msgs:
                spams[user_id]["banned"] = time.time() + ban
                # text = """You're banned for {} minutes""".format(ban/60)
                # bot.send_message(user_id, text)
                # User is banned! alert him...
                return True
        else:
            spams[user_id]["messages"] = 1
            spams[user_id]["next_time"] = int(time.time()) + max
    return False


user_params = {}
last_time_stat = [0]
last_time_queue = [0]
last_time_help = [0]


def get_keyboard():
    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    key.add(types.InlineKeyboardButton(text='Ссылка на плейлист', callback_data="butt1"))
    key.add(types.InlineKeyboardButton(text='Вывести плейлист', callback_data="butt1"))
    key.add(types.InlineKeyboardButton(text='Вывести статистику', callback_data="butt2"))
    key.add(types.InlineKeyboardButton(text='Помощь', callback_data="butt3"))
    return key

def botactions():
    #Set all your bot handlers inside this function
    #If bot is used as a global variable, remove bot as an input param
    print('botactions')
    @bot.message_handler(content_types=['text'])
    def get_text_messages(message):
        # print(message.from_user.username)
        # print(message.from_user.id)
        # print(message.from_user.first_name)
        # print(message.from_user.last_name)
        if message.from_user.username not in USERNAME_WHITELIST:
            bot.send_message(message.from_user.id, "Прости, но твоего тега нет в списке\nЕсли считаешь, что это ошибка - напиши @nokrolikno", reply_markup=get_keyboard())
            return
        if is_spam(message.from_user.username):
            bot.send_message(message.from_user.id, "Подожди немного перед отправкой следующего сообщения -_-", reply_markup=get_keyboard())
            return
        with open('logs.txt', 'a', encoding='UTF-8') as f:
            dt = datetime.datetime.now()
            formatted = dt.strftime('%d.%m.%Y - %H:%M:%S')
            full_username = message.from_user.first_name + ' ' + f' ({message.from_user.username})'
            f.write(f'\n{formatted} - {full_username}\n{message.text}\n')
        user_params[message.from_user.id] = {'username': message.from_user.username}
        if message.text == '/start':
            start(message)
            return
        if message.text in {'/help', 'Помощь'}:
            if time.time() < last_time_help[0] + 1:
                bot.send_message(message.from_user.id, "Подожди немного -_-", reply_markup=get_keyboard())
                return
            last_time_help[0] = time.time()
            help(message)
            return
        if message.text in {'/q', 'Вывести плейлист'}:
            if time.time() < last_time_queue[0] + 1:
                bot.send_message(message.from_user.id, "Подожди немного -_-", reply_markup=get_keyboard())
                return
            last_time_queue[0] = time.time()
            print_tracks(message)
            return
        if message.text in {'/link', 'Ссылка на плейлист'}:
            bot.send_message(message.from_user.id, "Вот плейлист Туса 2:\nhttps://music.yandex.ru/users/vasya.ermakov.2001@mail.ru/playlists/1002")
            return
        if message.text in {'/stat', 'Вывести статистику'}:
            if time.time() < last_time_stat[0] + 5:
                bot.send_message(message.from_user.id, "Подожди немного -_-", reply_markup=get_keyboard())
                return
            last_time_stat[0] = time.time()
            p = ctx.Process(target=create_box_plot)
            p.start()
            time.sleep(1)
            p.join()
            p.kill()
            # create_box_plot(cursor)
            make_stat(message)
            return
        text = message.text
        if re.match(r'^https://music\.yandex\.ru/users/.+?/playlists/[0-9]+$', text):
            merge_playlists(message)
            return
        text = try_get_url(text)
        if not re.match(r'^https://music.yandex.ru/album/[0-9]+/track/[0-9]+$', text):
            bot.send_message(message.from_user.id, "Немного не понял :(", reply_markup=get_keyboard())
            return
        data = parse_url(text)
        user_params[message.from_user.id]['track_id'] = data['track']
        user_params[message.from_user.id]['album_id'] = data['album']
        user_params[message.from_user.id]['playlist_kind'] = get_playlist_kind(client)
        user_params[message.from_user.id]['playlist_revision'] = get_playlist_revision(client)
        if in_playlist(client, user_params[message.from_user.id]['playlist_kind'], user_params[message.from_user.id]['track_id']):
            bot.send_message(message.from_user.id, "Такой трек уже в плейлисте", reply_markup=get_keyboard())
        else:
            try:
                add_track(message)
            except Exception as e:
                bot.send_message(message.from_user.id, 'В процессе возникла ошибка :(', reply_markup=get_keyboard())
                with open('logs.txt', 'a', encoding='UTF-8') as f:
                    f.write(f'Вот тут ошибка!!!\n{e}\n')


    def add_track(message):
        keyboard = types.InlineKeyboardMarkup()  # наша клавиатура
        key_yes = types.InlineKeyboardButton(text='Да', callback_data='yes') # кнопка «Да»
        keyboard.add(key_yes)  # добавляем кнопку в клавиатуру
        key_no = types.InlineKeyboardButton(text='Нет', callback_data='no')
        keyboard.add(key_no)
        user_params[message.from_user.id]['name'], user_params[message.from_user.id]['artists'] = get_artists_and_name(
            client, user_params[message.from_user.id]['track_id']
        )
        question = f"Добавить\n{', '.join(user_params[message.from_user.id]['artists'])} - {user_params[message.from_user.id]['name']}?"
        bot.send_message(message.from_user.id, text=question, reply_markup=keyboard)

    def merge_playlists(message):
        bot.send_message(message.from_user.id, text="Начинаю слияние плейлистов")
        owner_id = message.text.split('/')[-3]
        playlist_id = message.text.split('/')[-1]
        playlist = Client().users_playlists(playlist_id, owner_id)
        kind = get_playlist_kind(client)
        all_tracks = [(track['track']['id'], track['track']['albums'][0]['id']) for track in playlist['tracks']]
        added_tracks = 0
        percent = 25
        for i, (track_id, album_id) in enumerate(all_tracks):
            try:
                if in_playlist(client, kind, track_id):
                    continue
                if track_in_db(cursor, track_id):
                    continue
                playlist_revision = get_playlist_revision(client)
                client.users_playlists_insert_track(
                    kind=kind, album_id=album_id, track_id=track_id, revision=playlist_revision
                )
                name, artists = get_artists_and_name(client, track_id)
                add_track_db(cursor, message.from_user.username, track_id, name, artists)
                added_tracks += 1
                db_connection.commit()
                if round(i / len(all_tracks) * 100) > percent:
                    bot.send_message(message.from_user.id,
                                     text=f"Слияние плейлистов завершено на {round(i / len(all_tracks) * 100, 1)}%")
                    percent += 25
            except Exception as e:
                print('Bad')
                db_connection.rollback()
        bot.send_message(message.from_user.id, text=f"Слияние плейлистов завершено\nДобавлено {added_tracks} треков", reply_markup=get_keyboard())


    @bot.callback_query_handler(func=lambda call: True)
    def callback_worker(call):
        if call.data == "yes": #call.data это callback_data, которую мы указали при объявлении кнопки
            try:
                playlist_revision, playlist_kind, track_id, album_id, name, artists = (
                    user_params[call.message.chat.id]['playlist_revision'],
                    user_params[call.message.chat.id]['playlist_kind'],
                    user_params[call.message.chat.id]['track_id'],
                    user_params[call.message.chat.id]['album_id'],
                    user_params[call.message.chat.id]['name'],
                    user_params[call.message.chat.id]['artists'],
                )
                if in_playlist(client, playlist_kind, track_id):
                    bot.send_message(call.message.chat.id, 'Такой трек уже в плейлисте', reply_markup=get_keyboard())
                    return
                if track_in_db(cursor, track_id):
                    bot.send_message(call.message.chat.id, 'Такой трек уже в плейлисте', reply_markup=get_keyboard())
                    return
                playlist_revision = get_playlist_revision(client)
                client.users_playlists_insert_track(
                    kind=playlist_kind, album_id=album_id, track_id=track_id, revision=playlist_revision
                )
                add_track_db(cursor, user_params[call.message.chat.id]['username'], track_id, name, artists)
                bot.send_message(call.message.chat.id, 'Всё с кайфом, добавил :)', reply_markup=get_keyboard())
                db_connection.commit()
            except KeyError as e:
                bot.send_message(call.message.chat.id, f'Эта кнопка более не действительна :(', reply_markup=get_keyboard())
            except Exception as e:
                db_connection.rollback()
                bot.send_message(call.message.chat.id, 'В процессе возникла ошибка :(', reply_markup=get_keyboard())
                with open('logs.txt', 'a', encoding='UTF-8') as f:
                    f.write(f'Вот тут ошибка!!!\n{e}\n')
        elif call.data == "no":
            bot.send_message(call.message.chat.id, 'Ну лан.. :|', reply_markup=get_keyboard())


    def start(message):
        key = get_keyboard()
        msg = bot.send_message(message.chat.id, f"Привет {message.from_user.username}! Просто кинь ссылочку на трек и я добавлю его в плейлист 'Туса 2.0' !!!" +
                         "\nПодробнее /help", reply_markup=key)
        if message.from_user.username == 'Shekkell':
            bot.send_message(message.from_user.id, "Сань, я знаю что это ты. Потести плз :)")


    def help(message):
        bot.send_message(
            message.from_user.id,
            """
    Приветули!
    Всё проще некуда. Кидай сюда ссылочку на песенку из ЯМ
    Она выглядит типа вот так:
    https://music.yandex.ru/album/12345332/track/72050048
    
    Ещё можешь написать /q и посмотреть все треки в плейлисте на текущий момент
    Напиши /stat и узнаешь статистику на текущий момент

    По вопросам работы с ботом пиши @nokrolikno
    
    Ну и всё в принципе
            """, reply_markup=get_keyboard()
        )


    def print_tracks(message):
        all_tracks = get_all_tracks_db(cursor)
        all_tracks_str = map(lambda x: x[1] + ' - ' + x[0], all_tracks)
        response = ''
        for i, track in enumerate(all_tracks_str):
            response += f'{i + 1}. {track}\n'
        response = response.strip()
        if response == "":
            bot.send_message(message.from_user.id, "Плейлист пока пуст :(", reply_markup=get_keyboard())
        else:
            bot.send_message(message.from_user.id, response, reply_markup=get_keyboard())


    def make_stat(message):
        cursor.execute("SELECT username, COUNT(*) FROM Actions GROUP BY username ORDER BY 2 DESC;")
        if cursor.rowcount == 0:
            filename = "empty_statistics.png"
        else:
            filename = "statistics.png"
        bot.send_photo(message.from_user.id, photo=open(filename, 'rb'), caption="Вот кто сколько треков накидал")
        bot.send_message(message.from_user.id, f"Самый популярный исполнитель на тусе — это\.\.\.  ||{most_popular_artist(cursor).replace('!', '')}||", parse_mode='MarkdownV2', reply_markup=get_keyboard())


def bot_polling():
    global bot #Keep the bot object as global variable if needed
    print("Starting bot polling now")
    while True:
        try:
            print("New bot instance started")
            bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False) #Generate new bot instance
            botactions() #If bot is used as a global variable, remove bot as an input param
            bot.polling(none_stop=True, interval=BOT_INTERVAL, timeout=BOT_TIMEOUT)
        except Exception as ex: #Error in polling
            print("Bot polling failed, restarting in {}sec. Error:\n{}".format(BOT_TIMEOUT, ex))
            global cursor, db_connection
            cursor, db_connection = get_cursor()
            bot.stop_polling()
            time.sleep(BOT_TIMEOUT)
        else: #Clean exit
            bot.stop_polling()
            print("Bot polling loop finished")
            break #End loop


polling_thread = threading.Thread(target=bot_polling)
polling_thread.daemon = True
polling_thread.start()


if __name__ == "__main__":
    while True:
        try:
            time.sleep(120)
        except KeyboardInterrupt:
            break



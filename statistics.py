import sys
import time

import seaborn as sns
import matplotlib.pyplot as plt
import mariadb

from functools import reduce

from dbhelper import DBCursor, get_cursor
from config import STATISTICS_UPDATE


names = {
    'nokrolikno': 'Вася',
    'estun_d': 'Егор',
    'saltstraumen_bb': 'Настя',
    'bullshit_so': 'Соня',
    'hatememooore': 'Макс',
    'akakiy_kos9lk': 'Даня',
    'Ane4kaAiz': 'Аня',
    'Danchhh': 'Валуч',
    'Shekkell': 'Саня',
}


def create_box_plot() -> str:
    cursor, conn = get_cursor()
    with open('statistics_logs.txt', 'w', encoding='UTF-8') as f:
        f.write(str(time.time()))
    cursor.execute("SELECT username, COUNT(*) FROM Actions GROUP BY username ORDER BY 2 DESC;")
    if cursor.rowcount == 0:
        sys.exit()
    active_users = list(cursor)
    X = []
    Y = []
    for user, value in active_users:
        Y.append(names[user])
        X.append(value)
    sns.set_theme(style="whitegrid")
    fig, axis = plt.subplots(1, 1)
    fig.set_figheight(6)
    fig.set_figwidth(11)
    sns.barplot(x=X, y=Y, width=0.5)
    plt.tick_params(axis='both', which='major', labelsize=14)
    plt.savefig('statistics.png')
    plt.close(fig)
    sys.exit()


def most_popular_artist(cursor: mariadb.Cursor):
    cursor.execute("SELECT artists FROM Actions;")
    if cursor.rowcount == 0:
        return 'Никто :\) Плейлист пока пуст\!'
    artists = list(cursor)
    artists = list(map(lambda x: x[0].split(', '), artists))
    artists_reduced = reduce(lambda a, b: a + b, artists)
    return max(set(artists_reduced), key=artists_reduced.count)


def main():
    cursor, conn = DBCursor()
    while True:
        create_box_plot(cursor)
        time.sleep(STATISTICS_UPDATE)


if __name__ == "__main__":
    main()

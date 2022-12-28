# Module Imports
import mariadb
import sys


class DBCursor:
    _cursor = None
    _conn = None

    def __new__(cls):
        if not cls._cursor and not cls._conn:
            try:
                cls._conn = mariadb.connect(
                    user="root",
                    password="Vasya0712",
                    host="localhost",
                    port=3306,
                    database="tusa"

                )
            except mariadb.Error as e:
                print(f"Error connecting to MariaDB Platform: {e}")
                sys.exit(1)

            # Get Cursor
            cls._cursor = cls._conn.cursor()
        return cls._cursor, cls._conn


def get_cursor():
    # Connect to MariaDB Platform
    try:
        conn = mariadb.connect(
            user="root",
            password="Vasya0712",
            host="localhost",
            port=3306,
            database="tusa"

        )
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        sys.exit(1)

    # Get Cursor
    cur = conn.cursor()
    return cur, conn


def track_in_db(cursor: mariadb.Cursor, track_id):
    cursor.execute('SELECT track_id FROM Actions WHERE track_id=%s;', (track_id,))
    return cursor.rowcount != 0


def add_track_db(cursor: mariadb.Cursor, username, track_id, name, artists):
    cursor.execute(
        "INSERT INTO Actions (username, track_id, name, artists) VALUES(%s, %s, %s, %s);",
        (username, track_id, name, ', '.join(artists))
    )


def get_all_tracks_db(cursor: mariadb.Cursor):
    cursor.execute(
        "SELECT name, artists FROM ACTIONS;"
    )
    return list(cursor)


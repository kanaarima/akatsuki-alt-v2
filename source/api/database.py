from api.logging import get_logger
from config import config
import sqlite3

logger = get_logger("api.database")
conn = sqlite3.connect(
    config["database"], isolation_level=None, check_same_thread=False
)
conn_uri = sqlite3.connect(
    f"file:{config['database']}?mode=ro",
    isolation_level=None,
    check_same_thread=False,
    uri=True,
)


def create_beatmap_table(conn):
    c = conn.cursor()
    query = """CREATE TABLE "beatmaps" (
	"beatmap_id"	INTEGER NOT NULL UNIQUE,
	"beatmap_set_id"	INTEGER NOT NULL,
	"md5"	TEXT NOT NULL,
	"artist"	TEXT NOT NULL,
	"title"	TEXT NOT NULL,
	"difficulty_name"	TEXT NOT NULL,
	"mapper"	TEXT NOT NULL,
	"bancho_status"	INTEGER NOT NULL,
	"akatsuki_status"	INTEGER NOT NULL,
    "last_checked"	TEXT NOT NULL,
	"ar"	REAL NOT NULL,
	"od"	REAL NOT NULL,
	"cs"	REAL NOT NULL,
	"length"	REAL NOT NULL,
	"bpm"	REAL NOT NULL,
	"max_combo"	INTEGER NOT NULL,
	"circles"	INTEGER NOT NULL,
	"sliders"	INTEGER NOT NULL,
	"spinners"	INTEGER NOT NULL,
	"mode"	INTEGER NOT NULL,
	"tags"	TEXT NOT NULL,
    "stars_nm"	REAL DEFAULT "0" NOT NULL,
    "stars_ez"	REAL DEFAULT "0" NOT NULL,
    "stars_hr"	REAL DEFAULT "0" NOT NULL,
    "stars_dt"	REAL DEFAULT "0" NOT NULL,
    "stars_dtez"	REAL DEFAULT "0" NOT NULL,
    "stars_dthr"	REAL DEFAULT "0" NOT NULL,
	PRIMARY KEY("beatmap_id")
)"""
    c.execute(query)
    conn.commit()


def create_map_post_table(conn):
    c = conn.cursor()
    query = """CREATE TABLE "beatmaps_posts" (
	"beatmap_set_id"	INTEGER NOT NULL UNIQUE,
	"message_id"	INTEGER NOT NULL UNIQUE,
	"last_updated"	INTEGER NOT NULL,
	PRIMARY KEY("beatmap_set_id")
);"""
    c.execute(query)
    conn.commit()


def create_map_leaderboard_table(conn):
    c = conn.cursor()
    query = """CREATE TABLE "beatmaps_leaderboard" (
	"beatmap_id"	INTEGER NOT NULL,
	"mode"	INTEGER NOT NULL,
    "relax"	INTEGER NOT NULL,
    "last_update" INTEGER NOT NULL,
	"position"	INTEGER NOT NULL,
	"user_id"	INTEGER NOT NULL,
	"accuracy"	REAL NOT NULL,
	"mods"	INTEGER NOT NULL,
	"rank"	TEXT NOT NULL,
	"count_300"	INTEGER NOT NULL,
	"count_100"	INTEGER NOT NULL,
	"count_50"	INTEGER NOT NULL,
	"count_miss"	INTEGER NOT NULL,
    "date"		INTEGER NOT NULL,
    PRIMARY KEY("beatmap_id", "mode", "relax", "position")
);"""
    c.execute(query)
    conn.commit()


def create_metrics_table(conn):
    c = conn.cursor()
    query = """CREATE TABLE "metrics" (
	"endpoint"	TEXT NOT NULL UNIQUE,
	"requests"	INTEGER NOT NULL,
	"errors"	INTEGER NOT NULL,
	PRIMARY KEY("endpoint")
)"""
    c.execute(query)
    conn.commit()


def create_user_daily_1s_table(conn):
    c = conn.cursor()
    query = """CREATE TABLE "leaderboard_user_daily1s" (
	"user_id"	INTEGER NOT NULL UNIQUE,
	"date"	TEXT NOT NULL,
	"gamemode"	TEXT NOT NULL,
	"amount"	INTEGER,
	PRIMARY KEY("gamemode","date","user_id")
);"""
    c.execute(query)
    conn.commit()


def create_tables(conn):
    c = conn.cursor()
    c.execute(
        """ SELECT count(name) FROM sqlite_master WHERE type='table' AND name='beatmaps' """
    )
    if c.fetchone()[0] != 1:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.commit()
        create_beatmap_table(conn)
    c.execute(
        """ SELECT count(name) FROM sqlite_master WHERE type='table' AND name='beatmaps_posts' """
    )
    if c.fetchone()[0] != 1:
        create_map_post_table(conn)
    c.execute(
        """ SELECT count(name) FROM sqlite_master WHERE type='table' AND name='beatmaps_leaderboard' """
    )
    if c.fetchone()[0] != 1:
        create_map_leaderboard_table(conn)
    c.execute(
        """ SELECT count(name) FROM sqlite_master WHERE type='table' AND name='metrics' """
    )
    if c.fetchone()[0] != 1:
        create_metrics_table(conn)
    c.execute(
        """ SELECT count(name) FROM sqlite_master WHERE type='table' AND name='leaderboard_user_daily1s' """
    )
    if c.fetchone()[0] != 1:
        create_user_daily_1s_table(conn)


create_tables(conn)

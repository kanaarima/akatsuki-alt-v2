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


def table_exists(table_name):
    c = conn.cursor()
    c.execute(
        f""" SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{table_name}' """
    )
    return c.fetchone()[0] == 1


def get_task(task_name) -> int:
    c = conn.cursor()
    check = c.execute(
        "SELECT last_run FROM tasks WHERE name = ?", (task_name,)
    ).fetchone()
    if check:
        return check[0]
    else:
        return 0


def set_task(task_name, last_run):
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO tasks VALUES(?, ?)", (task_name, last_run))
    conn.commit()


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


# TODO FIX SHIT PP MISSING
def create_map_leaderboard_table(conn):
    c = conn.cursor()
    query = """CREATE TABLE "beatmaps_leaderboard" (
	"beatmap_id"	INTEGER NOT NULL,
	"mode"	INTEGER NOT NULL,
    "last_update" INTEGER NOT NULL,
	"position"	INTEGER NOT NULL,
	"user_id"	INTEGER NOT NULL,
	"accuracy"	REAL NOT NULL,
	"mods"	INTEGER NOT NULL,
	"pp"	REAL NOT NULL,
	"score"	INTEGER NOT NULL,
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
	"user_id"	INTEGER NOT NULL,
	"date"	TEXT NOT NULL,
	"gamemode"	TEXT NOT NULL,
	"amount"	INTEGER,
	PRIMARY KEY("gamemode","date","user_id")
);"""
    c.execute(query)
    conn.commit()


def create_tasks_table(conn):
    c = conn.cursor()
    query = """CREATE TABLE "tasks" (
	"name"	TEXT UNIQUE,
	"last_run"	INTEGER,
	PRIMARY KEY("name")
)"""
    c.execute(query)
    conn.commit()


def create_users_table(conn):
    c = conn.cursor()
    query = """CREATE TABLE "users" (
	"user_id"	INTEGER NOT NULL UNIQUE,
    "clan_id"   INTEGER NOT NULL,
	"name"	INTEGER,
	"country"	TEXT,
	"discord_id"	INTEGER NOT NULL UNIQUE,
	"default_mode"	INTEGER,
	PRIMARY KEY("user_id")
);"""
    c.execute(query)
    conn.commit()


def create_users_score_table(conn):
    c = conn.cursor()
    query = """CREATE TABLE "users_scores" (
	"beatmap_id"	INTEGER NOT NULL,
	"mode"	TEXT NOT NULL
	"score_id"	INTEGER NOT NULL,
	"user_id"	INTEGER NOT NULL,
	"accuracy"	REAL NOT NULL,
	"mods"	INTEGER NOT NULL,
	"pp"	REAL NOT NULL,
	"score"	INTEGER NOT NULL,
	"rank"	TEXT NOT NULL,
	"count_300"	INTEGER NOT NULL,
	"count_100"	INTEGER NOT NULL,
	"count_50"	INTEGER NOT NULL,
	"count_miss"	INTEGER NOT NULL,
    "date"		INTEGER NOT NULL,
    PRIMARY KEY("mode", "beatmap_id")
)"""
    c.execute(query)
    conn.commit()


def create_users_playtime_table(conn):
    c = conn.cursor()
    query = """CREATE TABLE "users_playtime" (
	"user_id"	INTEGER NOT NULL,
	"mode"	TEXT NOT NULL,
	"submitted_plays"	REAL NOT NULL,
	"unsubmitted_plays"	INTEGER NOT NULL,
	"most_played"	INTEGER NOT NULL,
    "last_score_id" INTEGER NOT NULL,
	PRIMARY KEY("user_id","mode")
);"""
    c.execute(query)
    conn.commit()


def create_tables(conn):
    if not table_exists("beatmaps"):
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.commit()
        create_beatmap_table(conn)
    if not table_exists("beatmaps_leaderboard"):
        create_map_leaderboard_table(conn)
    if not table_exists("metrics"):
        create_metrics_table(conn)
    if not table_exists("leaderboard_user_daily1s"):
        create_user_daily_1s_table(conn)
    if not table_exists("tasks"):
        create_tasks_table(conn)
    if not table_exists("users"):
        create_users_table(conn)
    if not table_exists("users_scores"):
        create_users_score_table(conn)
    if not table_exists("users_playtime"):
        create_users_playtime_table(conn)


create_tables(conn)

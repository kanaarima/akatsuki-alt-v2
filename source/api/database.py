from api.logging import get_logger
from config import config
import sqlite3

logger = get_logger("api.database")
conn = sqlite3.connect(config["database"])


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
	PRIMARY KEY("beatmap_id")
)"""
    c.execute(query)
    conn.commit()


def create_tables(conn):
    c = conn.cursor()
    c.execute(
        """ SELECT count(name) FROM sqlite_master WHERE type='table' AND name='beatmaps' """
    )
    if c.fetchone()[0] != 1:
        create_beatmap_table(conn)


create_tables(conn)

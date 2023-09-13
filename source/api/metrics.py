from api.logging import get_logger, type
import api.database as database
from api.files import DataFile
from config import config

logger = get_logger("api.metrics")


def log_request(request, post=False):
    error = 0
    type = "POST" if post else "GET"
    if request.status_code > 299:
        logger.warn(f"{type} {request.url} {request.status_code}")
        error = 1
    else:
        logger.info(f"{type} {request.url} {request.status_code}")
    method = request.url.split("?")[0]

    check = database.conn.execute(
        f'SELECT * FROM metrics WHERE endpoint = "global"'
    ).fetchall()
    if not check:
        database.conn.execute(
            f"""INSERT INTO "main"."metrics"(endpoint, requests, errors) VALUES (?,?,?) """,
            ("global", 0, 0),
        )

    check = database.conn.execute(
        f"SELECT * FROM metrics WHERE endpoint = ?", (method,)
    ).fetchall()
    if not check:
        database.conn.execute(
            f"""INSERT INTO "main"."metrics"(endpoint, requests, errors) VALUES (?,?,?) """,
            (method, 0, 0),
        )
    if error:
        database.conn.execute(
            f"""UPDATE metrics SET "errors" = errors + 1   WHERE endpoint = "?" """,
            (method,),
        )
        database.conn.execute(
            f"""UPDATE metrics SET "errors" = errors + 1   WHERE endpoint = "?" """,
            ("global",),
        )
    else:
        database.conn.execute(
            f"""UPDATE metrics SET "requests" = requests + 1   WHERE endpoint = "?" """,
            (method,),
        )
        database.conn.execute(
            f"""UPDATE metrics SET "requests" = requests + 1   WHERE endpoint = "?" """,
            ("global",),
        )
    database.conn.commit()


def log_command(command, full, message, wrong=False):
    logger.info(f"CMD {full} ({message.author.name}, {message.author.id})")
    pass

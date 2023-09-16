from api.logging import get_logger, type
from api.utils import execute
import api.database as database

logger = get_logger("api.metrics")


def log_request(request, post=False):
    cur = database.conn.cursor()
    error = 0
    type = "POST" if post else "GET"
    if request.status_code > 299:
        logger.warn(f"{type} {request.url} {request.status_code}")
        error = 1
    else:
        logger.info(f"{type} {request.url} {request.status_code}")
    method = request.url.split("?")[0]

    check = execute(cur, f'SELECT * FROM metrics WHERE endpoint = "global"').fetchall()
    if not check:
        execute(
            cur,
            f"""INSERT INTO "main"."metrics"(endpoint, requests, errors) VALUES (?,?,?) """,
            ("global", 0, 0),
        )

    check = execute(
        cur, f"SELECT * FROM metrics WHERE endpoint = ?", (method,)
    ).fetchall()
    if not check:
        execute(
            cur,
            f"""INSERT INTO "main"."metrics"(endpoint, requests, errors) VALUES (?,?,?) """,
            (method, 0, 0),
        )
    if error:
        execute(
            cur,
            f"""UPDATE metrics SET "errors" = errors + 1   WHERE endpoint = ? """,
            (method,),
        )
        execute(
            cur,
            f"""UPDATE metrics SET "errors" = errors + 1   WHERE endpoint = ? """,
            ("global",),
        )
    else:
        execute(
            cur,
            f"""UPDATE metrics SET "requests" = requests + 1   WHERE endpoint = ? """,
            (method,),
        )
        execute(
            cur,
            f"""UPDATE metrics SET "requests" = requests + 1   WHERE endpoint = ? """,
            ("global",),
        )
    cur.close()
    database.conn.commit()


def log_command(command, full, message, wrong=False):
    logger.info(f"CMD {full} ({message.author.name}, {message.author.id})")
    pass

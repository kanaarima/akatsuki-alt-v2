from api.logging import logger
from api.files import DataFile
from config import config

requests_sent = {}
commands_used = {}
wrong_commands_used = {}


def log_request(request):
    load_metrics()
    if request.status_code > 299:
        logger.warn(f"POST {request.url} {request.status_code}")
    else:
        logger.info(f"POST {request.url} {request.status_code}")
    method = request.url.split("?")[0]
    if method in requests_sent:
        requests_sent[method] += 1
    else:
        requests_sent[method] = 1
    save_metrics()


def log_command(command, full, message, wrong=False):
    load_metrics()
    logger.info(f"CMD {full} ({message.author.name}, {message.author.id})")
    dest = commands_used if not wrong else wrong_commands_used
    if command in dest:
        dest[command] += 1
    else:
        dest[command] = 1
    save_metrics()


def load_metrics():
    file = DataFile(f"{config['common']['data_directory']}/metrics.json.gz")
    file.load_data(
        default={"requests_sent": {}, "commands_used": {}, "wrong_commands_used": {}}
    )
    requests_sent = file.data["requests_sent"]
    commands_used = file.data["commands_used"]
    wrong_commands_used = file.data["wrong_commands_used"]


def save_metrics():
    file = DataFile(f"{config['common']['log_directory']}/metrics.json.gz")
    file.data = {
        "requests_sent": requests_sent,
        "commands_used": commands_used,
        "wrong_commands_used": wrong_commands_used,
    }
    file.save_data()


load_metrics()

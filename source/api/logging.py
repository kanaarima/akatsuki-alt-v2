from config import config
import logging.handlers
import logging
import gzip
import sys
import os

class ColorFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    cyan = "\x1b[96m"
    reset = "\x1b[0m"

    format_prefix = '[%(asctime)s] - <%(name)s> '
    format = '%(levelname)s: %(message)s'

    FORMATS = {
        logging.DEBUG:    grey + format_prefix            + format + reset,
        logging.INFO:     grey + format_prefix + cyan     + format + reset,
        logging.WARNING:  grey + format_prefix + yellow   + format + reset,
        logging.ERROR:    grey + format_prefix + red      + format + reset,
        logging.CRITICAL: grey + format_prefix + bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

class GZipRotator:
    def __call__(self, source, dest):
        os.rename(source, dest)
        f_in = open(dest, "rb")
        f_out = gzip.open("%s.gz" % dest, "wb")
        f_out.writelines(f_in)
        f_out.close()
        f_in.close()
        os.remove(dest)

os.makedirs(config['common']['log_directory'], exist_ok=True)

type = "frontend" if "frontend" in "".join(sys.argv) else "backend"
file_handler = logging.handlers.TimedRotatingFileHandler(
    filename=f"{config['common']['log_directory']}/debug_{type}.log",
    when="midnight",
    interval=1,
    backupCount=5,
)
file_handler.rotator = GZipRotator()

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(ColorFormatter())

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] - <%(name)s> %(levelname)s: %(message)s',
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(type)
logger.setLevel(logging.DEBUG)

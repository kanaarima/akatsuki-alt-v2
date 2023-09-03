from config import config
import logging.handlers
import logging
import gzip
import sys
import os


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

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] - <%(name)s> %(levelname)s: %(message)s',
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(type)
logger.setLevel(logging.DEBUG)

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


type = "frontend" if "frontend" in "".join(sys.argv) else "backend"
logformatter = logging.Formatter("%(asctime)s;%(levelname)s;%(message)s")
log = logging.handlers.TimedRotatingFileHandler(
    f"{config['common']['log_directory']}/debug_{type}.log",
    "midnight",
    1,
    backupCount=5,
)
log.setLevel(logging.DEBUG)
log.setFormatter(logformatter)
log.rotator = GZipRotator()
logger = logging.getLogger("main")
logger.addHandler(log)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.DEBUG)

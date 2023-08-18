import json
import sys

try:
    with open("config.json") as f:
        config = json.load(f)
except Exception as e:
    print(f"{e} occurred.")
    sys.exit(-1)

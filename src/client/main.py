import csv
import logging
import os
import signal
import sys
from .client import Client
from common.enums import ExitCode

SERVER_HOST = os.environ["SERVER_HOST"]
SERVER_PORT = int(os.environ["SERVER_PORT"])
INPUT_FILE = os.environ["INPUT_FILE"]

def main():
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(ExitCode.SUCCESS))
    client = Client()
    try:
        client.connect(SERVER_HOST, SERVER_PORT)
        results = client.process_articles(INPUT_FILE)
        client.save_results(results)
    except (OSError, EOFError, ValueError, KeyError, csv.Error) as exc:
        logging.error("Client failed: %s", exc)
        return ExitCode.ERROR
    finally:
        client.disconnect()
    return ExitCode.SUCCESS


if __name__ == "__main__":
    sys.exit(main())

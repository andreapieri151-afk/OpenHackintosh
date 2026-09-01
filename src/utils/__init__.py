import logging
import os


def setup_logging(dev: bool = False) -> None:
    level = logging.DEBUG if dev else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
    if dev:
        os.environ.setdefault("OPENHACKINTOSH_DEV", "1")

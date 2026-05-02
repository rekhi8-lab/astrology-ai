import logging

from bot.telegram_handler import run
from ephemeris.loader import load_all


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


if __name__ == "__main__":
    configure_logging()
    load_all()
    print("Ephemeris loaded at startup")
    run()

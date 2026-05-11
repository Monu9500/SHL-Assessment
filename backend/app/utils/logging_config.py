import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    normalized = getattr(logging, str(level).upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(normalized)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root.handlers.clear()
    root.addHandler(handler)

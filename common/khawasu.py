from tinydb import TinyDB, Query
import config
from driver_khawasu.driver import LogicalDriver

_khawasu_driver = None


def driver() -> LogicalDriver:
    global _khawasu_driver
    if _khawasu_driver is None:
        _khawasu_driver = LogicalDriver(config.KHAWASU_ADDR, config.KHAWASU_PORT)
        _khawasu_driver.DEBUG_MODE = True

    return _khawasu_driver

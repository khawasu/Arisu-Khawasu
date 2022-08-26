from tinydb import TinyDB, Query

import config

_db = None


def db() -> TinyDB:
    global _db
    if _db is None:
        _db = TinyDB(config.DATABASE_PATH)

    return _db

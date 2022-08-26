import random
import string
import time

from tinydb import Query

from common.db import db


class Token:
    TOKEN_CODE_DEFAULT_LENGTH = 8
    TOKEN_ACCESS_DEFAULT_LENGTH = 32
    MAX_DELAY_TIME = 10

    def __init__(self, value: str, username: str, state: str, generated_time: int):
        self.value = value
        self.username = username
        self.generated_time = generated_time
        self.state = state

    def check_expired(self):
        return time.time() - self.generated_time > Token.MAX_DELAY_TIME

    def save(self):
        db().table("tokens").insert(self.get_row_object())

    def revoke(self):
        db().table("tokens").remove(Query().value == self.value)

    def get_row_object(self):
        return {"value": self.value, "username": self.username, "state": self.state,
                "generated_time": self.generated_time}

    @classmethod
    def get_by_value(cls, value: str):
        _token = Query()
        rows = db().table("tokens").search(_token.value == value)
        return None if len(rows) == 0 else cls.from_row_object(rows[0])

    @classmethod
    def _emit(cls, value: str, username: str, state: str):
        new_token = Token(value, username, state, int(time.time()))
        new_token.save()

        return new_token

    @classmethod
    def generate(cls, username: str, length: int, state: str = 0):
        chars = string.ascii_letters + string.digits
        value = ''.join(random.choice(chars) for i in range(length))

        return cls._emit(value, username, state)

    @classmethod
    def from_row_object(cls, row):
        return cls(row["value"], row["username"], row["state"], row["generated_time"])

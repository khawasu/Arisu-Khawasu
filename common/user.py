import hashlib

import bcrypt as bcrypt
from tinydb import Query

from common.db import db


class User:
    def __init__(self, id: int, username: str, password_hash: str, salt: str):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.salt = salt

    def remove(self):
        pass

    def hash_password(self, password: str):
        return bcrypt.hashpw(password.encode(), self.salt.encode()).decode()

    def get_row_object(self):
        return {"id": self.id, "username": self.username, "password_hash": self.password_hash, "salt": self.salt}

    def save(self):
        db().table("users").insert(self.get_row_object())

    @classmethod
    def create(cls, username: str, password: str):
        salt = bcrypt.gensalt().decode()
        password_hash = bcrypt.hashpw(password.encode(), salt.encode()).decode()

        new_user = cls(0, username, password_hash, salt)
        new_user.save()

        return new_user

    @classmethod
    def from_row_object(cls, row):
        return cls(row["id"], row["username"], row["password_hash"], row["salt"])

    @classmethod
    def get_by_username(cls, username: str):
        User = Query()
        user_row = db().table("users").search(User.username == username)
        return None if len(user_row) == 0 else cls.from_row_object(user_row[0])

    @classmethod
    def get_by_id(cls, id: int):
        User = Query()
        user_row = db().table("users").search(User.id == id)
        return None if len(user_row) == 0 else cls.from_row_object(user_row[0])


def check_login(user: User, password: str):
    return user is not None and user.password_hash == user.hash_password(password)

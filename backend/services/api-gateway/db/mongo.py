import datetime

from bson.objectid import ObjectId
from pymongo import ASCENDING, MongoClient


class UserStore:
    """MongoDB-backed store for auth user accounts."""

    def __init__(self, uri: str, db_name: str):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.users = self.db["users"]
        self.users.create_index([("username", ASCENDING)], unique=True)

    def find_by_username(self, username: str) -> dict | None:
        return self.users.find_one({"username": username})

    def find_by_id(self, user_id: str) -> dict | None:
        try:
            oid = ObjectId(user_id)
        except Exception:
            return None
        return self.users.find_one({"_id": oid})

    def admin_exists(self) -> bool:
        return self.users.count_documents({"role": "admin"}, limit=1) > 0

    def create_user(
        self,
        username: str,
        password_hash: str,
        role: str,
        staff_id: int | None,
    ) -> str:
        doc = {
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "staff_id": staff_id,
            "created_at": datetime.datetime.utcnow(),
        }
        result = self.users.insert_one(doc)
        return str(result.inserted_id)

import datetime

from bson.objectid import ObjectId
from pymongo import ASCENDING, MongoClient

from db.base import AbstractUserStore, UserRecord


class MongoUserStore(AbstractUserStore):
    """MongoDB-backed store for auth user accounts."""

    def __init__(self, uri: str, db_name: str):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.users = self.db["users"]
        self.users.create_index([("username", ASCENDING)], unique=True)

    @staticmethod
    def _to_record(doc: dict) -> UserRecord:
        return {
            "user_id": str(doc["_id"]),
            "username": doc["username"],
            "password_hash": doc["password_hash"],
            "role": doc.get("role", "user"),
            "staff_id": doc.get("staff_id"),
            "created_at": doc.get("created_at"),
        }

    def find_by_username(self, username: str) -> UserRecord | None:
        doc = self.users.find_one({"username": username})
        return self._to_record(doc) if doc else None

    def find_by_id(self, user_id: str) -> UserRecord | None:
        try:
            oid = ObjectId(user_id)
        except Exception:
            return None
        doc = self.users.find_one({"_id": oid})
        return self._to_record(doc) if doc else None

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

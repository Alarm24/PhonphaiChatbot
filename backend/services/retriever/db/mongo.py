import datetime
import os

from bson.objectid import ObjectId
from logger import log
from pymongo import MongoClient


class MongoDB:
    def __init__(self):
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.client = MongoClient(uri)
        self.db = self.client["rag_db"]
        self.files_collection = self.db["files"]

    def save_file(self, filename, theme, content_bytes, content_type):
        """Saves raw file metadata and content"""
        file_doc = {
            "file_name": filename,
            "theme": theme,
            "content_type": content_type,
            "size_bytes": len(content_bytes),
            "created_at": datetime.datetime.utcnow(),
            # In a real heavy production, store binary in GridFS or S3.
            # For this RAG setup, storing text/binary < 16MB is fine in doc.
            "data": content_bytes,
        }
        result = self.files_collection.insert_one(file_doc)
        return str(result.inserted_id)

    def list_files(self, theme_enum):
        """Returns list of files filtered by theme"""
        cursor = self.files_collection.find({"theme": theme_enum})
        return list(cursor)

    def get_file(self, file_id):
        return self.files_collection.find_one({"_id": ObjectId(file_id)})

    def get_all_files(self):
        """Fetch all files metadata from MongoDB"""
        files = []
        for doc in self.files_collection.find().sort("created_at", -1):
            files.append(
                {
                    "file_id": str(doc["_id"]),
                    "file_name": doc.get("file_name", "Unknown"),
                    "theme": doc.get("theme", "Unknown"),
                    "created_at": doc.get("created_at").isoformat()
                    if doc.get("created_at")
                    else "",
                    "size_bytes": doc.get("size_bytes", 0),
                }
            )
        return files

    def delete_file(self, file_id: str):
        """Delete file from MongoDB collection"""
        try:
            self.files_collection.delete_one({"_id": ObjectId(file_id)})
            return True
        except Exception as e:
            log.error(f"Mongo delete error: {e}")
            return False

import grpc
import retriever_pb2
import retriever_pb2_grpc
from config import get_settings
from db.mongo import MongoDB
from langchain_text_splitters import RecursiveCharacterTextSplitter
from logger import log
from themes.disaster import DisasterTheme
from themes.manual import ManualTheme
from utils.openrouter_parser import process_and_chunk_pdf_with_openrouter


class RetrieverServicer(retriever_pb2_grpc.RetrieverServiceServicer):
    def __init__(self):
        self.mongo = MongoDB()
        self.themes = {
            retriever_pb2.DISASTER: DisasterTheme(),
            retriever_pb2.MANUAL: ManualTheme(),
        }

    def Search(self, request, context):
        """Route search to the correct theme handler"""
        log.info(f"🔍 Searching Theme: {request.theme} for '{request.query}'")

        handler = self.themes.get(request.theme)
        if not handler:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid Theme")

        results = handler.search(request.query, request.limit)

        response_items = []
        for r in results:
            response_items.append(
                retriever_pb2.SearchResponse.Result(
                    content=r["content"],
                    file_name=r["metadata"].get("source", "unknown"),
                    page=r["metadata"].get("page", "Unknown"),
                    score=float(r["score"]),
                )
            )

        return retriever_pb2.SearchResponse(results=response_items)

    def UploadFile(self, request_iterator, context):
        data = bytearray()
        metadata = None

        try:
            first_msg = next(request_iterator)
            if not first_msg.HasField("info"):
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "First message must be metadata")

            metadata = first_msg.info
            log.info(f"📥 Receiving file: {metadata.file_name} [{metadata.theme}]")

            for request in request_iterator:
                if request.HasField("chunk_data"):
                    data.extend(request.chunk_data)

            final_bytes = bytes(data)

            # Save to MongoDB
            file_id = self.mongo.save_file(
                metadata.file_name, metadata.theme, final_bytes, metadata.content_type
            )

            handler = self.themes.get(metadata.theme)
            if handler:
                if "pdf" in metadata.content_type:
                    chunks = process_and_chunk_pdf_with_openrouter(final_bytes, metadata.file_name)
                    handler.add_knowledge(chunks, metadata.file_name)
                    log.info(
                        f"✅ Indexed {len(chunks)} overlapping page chunks for {metadata.file_name}"
                    )
                else:
                    # Fallback for plain text files (.txt, .md)
                    raw_text = final_bytes.decode("utf-8", errors="ignore")
                    settings = get_settings()
                    text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=settings.CHUNK_SIZE,
                        chunk_overlap=settings.CHUNK_OVERLAP,
                    )
                    text_chunks = text_splitter.create_documents([raw_text])

                    formatted_chunks = []
                    for doc in text_chunks:
                        formatted_chunks.append(
                            {
                                "content": doc.page_content,
                                "metadata": {"source": metadata.file_name, "page": "[1,1]"},
                            }
                        )

                    handler.add_knowledge(formatted_chunks, metadata.file_name)
                    log.info(f"✅ Indexed {len(text_chunks)} text chunks for {metadata.file_name}")

            return retriever_pb2.UploadFileResponse(
                file_id=file_id, message="File uploaded and indexed successfully", success=True
            )

        except Exception as e:
            log.error(f"❌ Upload Error: {e}")
            return retriever_pb2.UploadFileResponse(success=False, message=str(e))

    def ListFiles(self, request, context):
        try:
            db_files = self.mongo.get_all_files()
            response_files = []

            for f in db_files:
                response_files.append(
                    retriever_pb2.FileInfo(
                        file_id=f["file_id"],
                        file_name=f["file_name"],
                        theme=str(f["theme"]),
                        created_at=f["created_at"],
                        size_bytes=f["size_bytes"],
                    )
                )

            return retriever_pb2.ListFilesResponse(files=response_files)
        except Exception as e:
            log.error(f"Error listing files: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))

    def DeleteFile(self, request, context):
        log.info(f"🗑️ Deleting file: {request.filename} ({request.file_id})")

        try:
            # 1. Delete from MongoDB
            self.mongo.delete_file(request.file_id)

            # 2. Delete from the vector store
            theme_key = request.theme.lower()

            theme_map = {
                "remedy": retriever_pb2.REMEDY,
                "disaster": retriever_pb2.DISASTER,
                "manual": retriever_pb2.MANUAL,
            }

            enum_key = theme_map.get(theme_key)
            handler = self.themes.get(enum_key)

            if handler:
                handler.delete_knowledge(request.filename)
            else:
                log.warning(f"Theme handler not found for: {theme_key}")

            return retriever_pb2.DeleteFileResponse(
                success=True, message=f"Successfully deleted {request.filename}"
            )
        except Exception as e:
            log.error(f"❌ Error deleting file: {e}")
            return retriever_pb2.DeleteFileResponse(success=False, message=str(e))

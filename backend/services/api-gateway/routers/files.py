import grpc
import retriever_pb2
from config import Settings, get_settings
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from logger import log
from state import gRPCState

router = APIRouter()


async def chunk_generator(
    content: bytes, filename: str, content_type: str, theme_enum: int, chunk_size: int
):
    """
    Async generator to stream metadata and file chunks via gRPC.
    The protobuf definition requires the first message to be FileMetadata,
    and all subsequent messages to be the chunk_data.
    """
    # 1. First message MUST be the metadata
    yield retriever_pb2.UploadFileRequest(
        info=retriever_pb2.FileMetadata(
            file_name=filename,
            theme=theme_enum,
            content_type=content_type or "application/octet-stream",
        )
    )

    # 2. Subsequent messages are the file chunks
    for i in range(0, len(content), chunk_size):
        chunk = content[i : i + chunk_size]
        yield retriever_pb2.UploadFileRequest(chunk_data=chunk)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    theme: str = Form(..., description="Must be one of: remedy, disaster, manual"),
    settings: Settings = Depends(get_settings),  # Injects config efficiently
):
    """Uploads a file and streams it to the Retriever microservice."""
    try:
        # Map the string theme from the HTTP form to the gRPC Enum
        theme_map = {
            "remedy": retriever_pb2.REMEDY,
            "disaster": retriever_pb2.DISASTER,
            "manual": retriever_pb2.MANUAL,
        }

        # Validate theme
        theme_lower = theme.lower()
        if theme_lower not in theme_map:
            raise HTTPException(
                status_code=400,
                detail="Invalid theme. Must be remedy, disaster, or manual.",
            )

        theme_enum = theme_map[theme_lower]

        # Read the file content into memory
        content = await file.read()

        # Create our async stream generator
        request_iterator = chunk_generator(
            content=content,
            filename=file.filename,
            content_type=file.content_type,
            theme_enum=theme_enum,
            chunk_size=settings.CHUNK_SIZE,
        )

        # Use the persistent gRPC client that was opened on startup!
        client = gRPCState.retriever_client

        # Stream the chunks to the Retriever Service
        response = await client.UploadFile(request_iterator)

        if not response.success:
            raise HTTPException(status_code=500, detail=response.message)

        return {
            "file_id": response.file_id,
            "message": response.message,
            "success": response.success,
        }

    except grpc.RpcError as e:
        raise HTTPException(status_code=502, detail=...) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/")
async def list_documents(theme: str, settings: Settings = Depends(get_settings)):
    """Fetches a list of indexed files for a specific theme from the Retriever."""
    try:
        theme_map = {
            "remedy": retriever_pb2.REMEDY,
            "disaster": retriever_pb2.DISASTER,
            "manual": retriever_pb2.MANUAL,
        }

        theme_lower = theme.lower()
        if theme_lower not in theme_map:
            raise HTTPException(
                status_code=400,
                detail="Invalid theme. Must be remedy, disaster, or manual.",
            )

        theme_enum = theme_map[theme_lower]

        # Use the persistent client
        client = gRPCState.retriever_client
        request = retriever_pb2.ListFilesRequest(theme=theme_enum)

        response = await client.ListFiles(request)

        # Format the protobuf response into a clean JSON dictionary for the REST API
        return {
            "theme": theme_lower,
            "files": [
                {
                    "file_id": f.file_id,
                    "file_name": f.file_name,
                    "created_at": f.created_at,
                    "size_bytes": f.size_bytes,
                }
                for f in response.files
            ],
        }

    except grpc.RpcError as e:
        raise HTTPException(status_code=502, detail=...) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/")
async def list_files():
    """Get a list of all uploaded files across all themes"""
    try:
        request = retriever_pb2.ListFilesRequest()
        response = await gRPCState.retriever_client.ListFiles(request)
        
        return {
            "files": [
                {
                    "file_id": f.file_id, 
                    "file_name": f.file_name,
                    "theme": f.theme,
                    "created_at": f.created_at,
                    "size_bytes": f.size_bytes
                } for f in response.files
            ]
        }
    except Exception as e:
        log.error(f"Failed to fetch files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{file_id}")
async def delete_file(file_id: str, filename: str, theme: str):
    """Delete a file from both MongoDB and ChromaDB"""
    try:
        request = retriever_pb2.DeleteFileRequest(file_id=file_id, filename=filename, theme=theme)
        response = await gRPCState.retriever_client.DeleteFile(request)

        if not response.success:
            raise HTTPException(status_code=400, detail=response.message)

        return {"success": True, "message": response.message}
    except Exception as e:
        log.error(f"Failed to delete file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e

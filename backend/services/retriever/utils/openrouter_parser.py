import base64
import json

import requests
from config import get_settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from logger import log
from utils.prompt import PHARSER_PROMPT


def process_and_chunk_pdf_with_openrouter(file_bytes: bytes, filename: str) -> list:
    settings = get_settings()
    api_key = settings.OPENROUTER_API_KEY

    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured in environment.")

    log.info(f"🚀 Preparing {filename} for OpenRouter API...")
    base64_pdf = base64.b64encode(file_bytes).decode("utf-8")
    file_data_url = f"data:application/pdf;base64,{base64_pdf}"

    schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "pdf_page_chunks",
            "schema": {
                "type": "object",
                "properties": {
                    "pages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "page_number": {"type": "integer"},
                                "markdown_content": {"type": "string"},
                            },
                            "required": ["page_number", "markdown_content"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["pages"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }

    # Use the prompt you defined, or fallback to this inline one
    prompt = PHARSER_PROMPT

    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "file", "file": {"filename": filename, "file_data": file_data_url}},
                ],
            }
        ],
        "response_format": schema,
        "temperature": 0.1,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.APP_URL,
        "X-Title": "PhonphaiChatbot",
    }

    log.info(f"🧠 Parsing {filename} with OpenRouter...")
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers
    )

    if response.status_code != 200:
        raise Exception(f"OpenRouter Error: {response.text}")

    response_data = response.json()

    try:
        # --- 1. Extract Pages ---
        content_str = response_data["choices"][0]["message"]["content"]
        result_json = json.loads(content_str)
        pages = result_json.get("pages", [])

        # --- 2. Map Page Boundaries ---
        combined_text = ""
        page_boundaries = []

        for page in pages:
            start_idx = len(combined_text)
            combined_text += page["markdown_content"] + "\n\n"
            end_idx = len(combined_text) - 1
            page_boundaries.append((page["page_number"], start_idx, end_idx))

        # --- 3. Chunk the combined text ---
        log.info("✂️ Splitting text into overlapping chunks...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            add_start_index=True,  # Critical: Tracks where the chunk started
        )
        docs = text_splitter.create_documents([combined_text])

        # --- 4. Assign Overlapping Pages to Chunks ---
        final_chunks = []
        for doc in docs:
            start_index = doc.metadata["start_index"]
            end_index = start_index + len(doc.page_content)

            start_page = None
            end_page = None

            # Check which pages this specific chunk overlaps with
            for p_num, p_start, p_end in page_boundaries:
                if not (end_index < p_start or start_index > p_end):
                    if start_page is None:
                        start_page = p_num
                    end_page = p_num

            if start_page is None:
                start_page, end_page = 1, 1

            final_chunks.append(
                {
                    "content": doc.page_content,
                    "metadata": {
                        "source": filename,
                        "page": f"[{start_page},{end_page}]",  # e.g. [1,2] or [3,3]
                    },
                }
            )

        return final_chunks
    except Exception as e:
        log.error(f"Failed to parse and chunk OpenRouter response: {e}")
        raise e

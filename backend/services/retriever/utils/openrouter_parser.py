import base64
import json
import os

import requests
from config import get_settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langsmith import get_current_run_tree, traceable  # <-- Added imports
from logger import log
from utils.prompt import PHARSER_PROMPT


# --- 1. Create a traced helper function for the raw API call ---
@traceable(
    run_type="llm",
    metadata={"ls_provider": "openrouter", "ls_model_name": "google/gemini-2.5-flash"},
)
def call_openrouter_api(payload: dict, headers: dict) -> dict:
    """Handles the API call and tells LangSmith how many tokens were used."""
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers
    )

    if response.status_code != 200:
        raise Exception(f"OpenRouter Error: {response.text}")

    response_data = response.json()

    # Grab the tokens from the OpenRouter response and give them to LangSmith
    run = get_current_run_tree()
    if run and "usage" in response_data:
        usage = response_data["usage"]
        run.add_outputs({"usage": usage})

    return response_data


# --- 2. Update your main function ---
def process_and_chunk_pdf_with_openrouter(file_bytes: bytes, filename: str) -> list:
    settings = get_settings()
    api_key = settings.OPENROUTER_API_KEY

    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured in environment.")

    # --- LangSmith Configuration ---
    os.environ["LANGCHAIN_TRACING_V2"] = settings.LANGCHAIN_TRACING_V2
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT

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

    # --- Use the new helper function here! ---
    response_data = call_openrouter_api(payload, headers)

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
            add_start_index=True,
        )
        docs = text_splitter.create_documents([combined_text])

        # --- 4. Assign Overlapping Pages to Chunks ---
        final_chunks = []
        for doc in docs:
            start_index = doc.metadata["start_index"]
            end_index = start_index + len(doc.page_content)

            start_page = None
            end_page = None

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
                        "page": f"[{start_page},{end_page}]",
                    },
                }
            )

        return final_chunks
    except Exception as e:
        log.error(f"Failed to parse and chunk OpenRouter response: {e}")
        raise e

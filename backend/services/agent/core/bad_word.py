import re

import requests
from logger import log

# ==========================================
# --- GUARDRAIL CONFIGURATION ---
# ==========================================

# 1. Fetch English Bad Words
ENG_BAD_WORDS = []
try:
    resp = requests.get(
        "https://raw.githubusercontent.com/awdev1/better-profane-words/main/words.json"
    )
    resp.raise_for_status()
    eng_data = resp.json()

    if isinstance(eng_data, list) and len(eng_data) > 0 and isinstance(eng_data[0], dict):
        ENG_BAD_WORDS = [item.get("word") for item in eng_data if "word" in item]
    else:
        ENG_BAD_WORDS = eng_data
except Exception as e:
    log.warning(f"⚠️ Warning: Could not fetch English bad words. Error: {e}")
    ENG_BAD_WORDS = ["fallback_bad_word_1"]

# 2. Define Thai Bad Words & Ignore Words
THAI_BAD_WORDS = [
    "ควย",
    "เหี้ย",
    "หี",
    "สัส",
    "เชี่ย",
    "แรด",
    "กระหรี่",
    "ชิบหาย",
    "ตอแหล",
    "ฟาย",
    "แม่ง",
    "แสด",
    "ถุย",
    "เดรัจฉาน",
    "ชาติชั่ว",
    "นรก",
    "ไอดอก",
    "หมอย",
    "เอ๋อ",
    "สัตว์",
    "จัญไร",
    "เลว",
    "ทราม",
    "สถุน",
    "ระยำ",
    "อัปรีย์",
    "ต่ำตม",
    "กาก",
    "ส้นตีน",
    "หิวตีน",
    "ขยะ",
    "ขี้แพ้",
    "บัดซบ",
    "จังไร",
    "โสโครก",
    "เฮงซวย",
    "ตลาดล่าง",
    "ควาย",
    "มึงตาย",
    "ปัญญาอ่อน",
    "เส็งเคร็ง",
    "โง่",
    "โง่เง่า",
    "กะหรี่",
    "ดอกทอง",
    "ดอกกระหรี่",
    "บ้า",
    "ควๅย",
    "มึง",
    "อีดอก",
    "หน้าปลวก",
    "พ่อมึง",
    "แม่มึง",
    "เย็ด",
    "เงี่ยน",
    "หน้าด้าน",
]

THAI_IGNORE_WORDS = [
    "หีบ",
    "สัสดี",
    "หน้าหีบ",
    "ตด",
    "กะหรี่ปั๊บ",
    "บ้าน",
    "เชี่ยว",
]

# 3. Compile Regex Patterns
ENG_PATTERN = (
    re.compile(rf"\b({'|'.join(re.escape(w) for w in ENG_BAD_WORDS)})\b", re.IGNORECASE)
    if ENG_BAD_WORDS
    else None
)

THAI_PATTERN = (
    re.compile(rf"({'|'.join(re.escape(w) for w in THAI_BAD_WORDS)})", re.IGNORECASE)
    if THAI_BAD_WORDS
    else None
)


def censor_bad_words(text: str) -> str:
    """Replaces English and Thai bad words with ***, protecting ignore words."""
    if not text:
        return text

    censored_text = text

    # 1. Censor English
    if ENG_PATTERN:
        censored_text = ENG_PATTERN.sub("***", censored_text)

    # 2. Censor Thai
    if THAI_PATTERN:
        # Step A: Hide the ignore words using a temporary placeholder
        for i, ignore_word in enumerate(THAI_IGNORE_WORDS):
            censored_text = censored_text.replace(ignore_word, f"__IGNORE_{i}__")

        # Step B: Censor the actual root bad words
        censored_text = THAI_PATTERN.sub("***", censored_text)

        # Step C: Put the innocent ignore words back
        for i, ignore_word in enumerate(THAI_IGNORE_WORDS):
            censored_text = censored_text.replace(f"__IGNORE_{i}__", ignore_word)

    return censored_text

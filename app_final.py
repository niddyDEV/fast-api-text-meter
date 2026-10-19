from fastapi import FastAPI, Query
import uvicorn
import logging
from pathlib import Path
from dotenv import load_dotenv
import os
from contextlib import asynccontextmanager
import re
from pydantic import BaseModel, field_validator
from collections import Counter

class TextRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Текст не может быть пустым")
        return value

def extract_words(text: str) -> list[str]:
    return re.findall(r"[^\W_]+", text)

# Настройка значений сервиса
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)
APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
try:
    READING_SPEED_WPM = int(os.getenv('READING_SPEED_WPM', '200'))
except ValueError as exc:
    raise ValueError("READING_SPEED_WPM должен быть целым положительным числом") from exc

if READING_SPEED_WPM <= 0:
    raise ValueError("READING_SPEED_WPM должен быть больше 0")

# Логирование
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
ALLOWED_LOG_LEVELS = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
if LOG_LEVEL not in ALLOWED_LOG_LEVELS:
    raise ValueError(f"LOG_LEVEL должен быть одним из {ALLOWED_LOG_LEVELS}")

logger = logging.getLogger('textmeter')
logger.setLevel(LOG_LEVEL)
logger.propagate = False

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        )
    )
    logger.addHandler(handler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("TextMeter запущен: version=%s, reading_speed_wpm=%s", app.version, READING_SPEED_WPM)
    try:
        yield
    finally:
        logger.info("TextMeter остановлен")

#FastAPI и эндпоинты
app = FastAPI(
    title='TextMeter',
    description='Service for text analyzing',
    version=APP_VERSION,
    lifespan=lifespan
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get('/version')
def version():
    return {"version": app.version}

@app.post('/text/stats')
def text_stats(data: TextRequest):
    text = data.text
    words = extract_words(text)
    
    result = {
        "words": len(words),
        "characters": len(text),
        "characters_without_spaces": sum(1 for char in text if not char.isspace()),
    }
    
    logger.info(
        'Статистика текста: words=%s, characters=%s, characters_without_spaces=%s',
        result["words"],
        result["characters"],
        result["characters_without_spaces"]
    )
    
    return result

@app.post('/text/reading-time')
def text_reading_time(data: TextRequest):
    words_count = len(extract_words(data.text))
    
    estimated_second = round(words_count / READING_SPEED_WPM * 60, 2)
    
    logger.info(
        'Время чтения текста: words_count=%s, speed_wpm=%s, estimated_second=%s',
        words_count,
        READING_SPEED_WPM,
        estimated_second,
    )
    
    return {
        'words': words_count,
        'reading_speed_wpm': READING_SPEED_WPM,
        'estimated_second': estimated_second,
    }

@app.post('/text/top-words')
def top_words(
    data: TextRequest,
    limit: int = Query(default=5, ge=1, le=20, description="Максимальное количество слов в результатах")
):
    words = extract_words(data.text.lower())
    words_count = Counter(words)
    
    sorted_words = sorted(words_count.items(), key=lambda item: (-item[1], item[0]))
    
    result = [
        {
            "word": word,
            "count": count,
        }
        for word, count in sorted_words[:limit]
    ]

    logger.info(
        'Анализ частоты слов: words_count=%s, limit=%s, result=%s',
        len(words),
        len(words_count),
        limit,
        len(result)
    )
    
    return {'top_words': result}

if __name__ == "__main__":
    uvicorn.run(app)
    


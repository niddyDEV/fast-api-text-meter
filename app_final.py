from fastapi import FastAPI
import uvicorn
import logging
from pathlib import Path
from dotenv import load_dotenv
import os
from contextlib import asynccontextmanager

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

# FastAPI эндпоинты
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

if __name__ == "__main__":
    uvicorn.run(app)


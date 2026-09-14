import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    HF_API_TOKEN = os.getenv("HF_API_TOKEN")
    UPLOAD_DIR = "uploaded_pdfs"
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "ragdb")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

settings = Settings()

# Upload klasörünü oluştur (yoksa)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
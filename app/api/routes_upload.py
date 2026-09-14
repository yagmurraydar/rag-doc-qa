import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.core.pdf_loader import load_pdf
from app.core.chunking import split_documents
from app.core.vectorstore import save_chunks
from app.models.schemas import UploadResponse
from app.config import settings

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyaları kabul edilir.")

    file_path = Path(settings.UPLOAD_DIR) / file.filename

    try:
        # Dosyayı diske kaydet
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Pipeline: yükle -> chunk'la -> embed et -> pgvector'a yaz
        documents = load_pdf(str(file_path))
        chunks = split_documents(documents)
        save_chunks(chunks)

        return UploadResponse(
            message="PDF başarıyla işlendi ve indekslendi.",
            file_name=file.filename,
            num_pages=len(documents),
            num_chunks=len(chunks),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"İşlem sırasında hata oluştu: {str(e)}")
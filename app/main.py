from fastapi import FastAPI
from app.api import routes_upload, routes_ask

app = FastAPI(
    title="RAG Doküman Soru-Cevap Sistemi",
    description="PDF dokümanlarını vektörleştirip semantik arama ile soru cevaplayan RAG sistemi.",
    version="1.0.0",
)

app.include_router(routes_upload.router, prefix="/api", tags=["Upload"])
app.include_router(routes_ask.router, prefix="/api", tags=["Ask"])


@app.get("/")
async def root():
    return {"status": "ok", "message": "RAG API çalışıyor. Detaylar için /docs adresine gidin."}
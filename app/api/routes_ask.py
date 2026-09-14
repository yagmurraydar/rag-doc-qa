from fastapi import APIRouter, HTTPException

from app.core.rag_chain import answer_question
from app.models.schemas import AskRequest, AskResponse, SourceInfo

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Soru boş olamaz.")

    try:
        result = answer_question(request.question, top_k=request.top_k)

        sources = [
            SourceInfo(source_file=s["source_file"], page=s["page"])
            for s in result["sources"]
        ]

        return AskResponse(answer=result["answer"], sources=sources)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cevap üretilirken hata oluştu: {str(e)}")
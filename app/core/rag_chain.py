import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from app.core.vectorstore import similarity_search

load_dotenv()

client = InferenceClient(
    token=os.getenv("HF_API_TOKEN")
)

PROMPT_TEMPLATE = """Aşağıdaki bağlamı kullanarak soruyu yanıtla.

Eğer cevap bağlamda yoksa:
"Bu bilgi dokümanda bulunmuyor."
de.

Bağlam:
{context}

Soru:
{question}
"""


def build_context(chunks: list[dict]) -> str:
    """Retrieval edilen chunk'ları tek bir context metnine birleştirir."""

    parts = []

    for c in chunks:
        parts.append(
            f"[Kaynak: {c['source_file']}, Sayfa: {c['page']}]\n"
            f"{c['content']}"
        )

    return "\n\n".join(parts)


def answer_question(question: str, top_k: int = 5) -> dict:
    """
    Soruyu alır, ilgili chunk'ları getirir,
    LLM'e context ile birlikte gönderir,
    cevabı ve kaynakları döner.
    """

    # 1. Retrieval
    chunks = similarity_search(
        question,
        top_k=top_k
    )

    # 2. Context oluştur
    context = build_context(chunks)

    # 3. Prompt oluştur
    prompt = PROMPT_TEMPLATE.format(
        context=context,
        question=question
    )

    # 4. Groq üzerinden LLM çağrısı
    response = client.chat_completion(
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        model="openai/gpt-oss-20b:groq",
        max_tokens=300,
        temperature=0.3,
    )

    # 5. Cevabı al
    answer = response.choices[0].message.content

    # 6. Kaynakları hazırla
    sources = [
        {
            "source_file": c["source_file"],
            "page": c["page"]
        }
        for c in chunks
    ]

    return {
        "answer": answer,
        "sources": sources,
    }
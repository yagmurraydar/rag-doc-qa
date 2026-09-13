from sentence_transformers import SentenceTransformer

_model = None

def get_embedding_model():
    """Modeli lazy-load eder, tekrar tekrar yüklenmesin diye cache'ler."""
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Metin listesini embedding vektörlerine çevirir."""
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()
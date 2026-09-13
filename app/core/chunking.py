from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def split_documents(
    documents: list[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[Document]:
    """
    Uzun Document'leri daha küçük, anlamlı chunk'lara böler.
    Overlap sayesinde chunk sınırlarında bağlam kaybı azaltılır.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],  # önce paragraf, sonra cümle, sonra kelime böler
    )

    chunks = splitter.split_documents(documents)

    # Her chunk'a benzersiz bir id ekleyelim (sonra pgvector'da referans için lazım olacak)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i

    return chunks
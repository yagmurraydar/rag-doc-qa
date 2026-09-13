from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from pathlib import Path


def load_pdf(file_path: str) -> list[Document]:
    """
    Bir PDF dosyasını yükler ve sayfa sayfa Document nesnelerine çevirir.
    Her Document, metadata olarak dosya adı ve sayfa numarası içerir.
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"PDF bulunamadı: {file_path}")

    loader = PyPDFLoader(file_path)
    documents = loader.load()

  
    file_name = Path(file_path).name
    for doc in documents:
        doc.metadata["source_file"] = file_name

    return documents
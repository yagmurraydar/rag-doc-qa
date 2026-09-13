import sys
sys.path.append(".")  # app modülünü import edebilmek için

from app.core.pdf_loader import load_pdf
from app.core.chunking import split_documents
from app.core.vectorstore import save_chunks

if __name__ == "__main__":
    # Test için bir PDF yolu ver (kendi PDF'ini indir, örn. test.pdf)
    pdf_path = "test.pdf"

    print("PDF yükleniyor...")
    docs = load_pdf(pdf_path)
    print(f"{len(docs)} sayfa yüklendi.")

    print("Chunk'lara bölünüyor...")
    chunks = split_documents(docs)
    print(f"{len(chunks)} chunk oluşturuldu.\n")

    # İlk 2 chunk'ı gösterelim, kontrol edelim
    for chunk in chunks[:2]:
        print("---")
        print("Metadata:", chunk.metadata)
        print("İçerik:", chunk.page_content[:200], "...")
        
        save_chunks(chunks)
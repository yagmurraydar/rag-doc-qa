import sys
sys.path.append(".")  # app modülünü import edebilmek için

from app.core.pdf_loader import load_pdf
from app.core.chunking import split_documents
from app.core.vectorstore import save_chunks

if __name__ == "__main__":
    
    pdf_path = "test.pdf"

    print("PDF yükleniyor...")
    docs = load_pdf(pdf_path)
    print(f"{len(docs)} sayfa yüklendi.")

    print("Chunk'lara bölünüyor...")
    chunks = split_documents(docs)
    print(f"{len(chunks)} chunk oluşturuldu.\n")

   
    for chunk in chunks[:2]:
        print("---")
        print("Metadata:", chunk.metadata)
        print("İçerik:", chunk.page_content[:200], "...")
        
        save_chunks(chunks)
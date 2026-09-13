from pgvector.psycopg2 import register_vector
import psycopg2
from psycopg2.extras import execute_values
from app.core.embeddings import embed_texts
from langchain_core.documents import Document
from pgvector import Vector

def get_connection():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="ragdb",
        user="postgres",
        password="postgres",
    )

    register_vector(conn)

    return conn


def save_chunks(chunks: list[Document]):
    """Chunk'ları embed edip pgvector tablosuna yazar."""

    texts = [chunk.page_content for chunk in chunks]
    embeddings = embed_texts(texts)

    conn = get_connection()
    cur = conn.cursor()

    rows = []

    for chunk, embedding in zip(chunks, embeddings):
        rows.append((
            chunk.page_content,
            Vector(embedding),
            chunk.metadata.get("source_file"),
            chunk.metadata.get("page"),
            chunk.metadata.get("chunk_id"),
        ))

    execute_values(
        cur,
        """
        INSERT INTO document_chunks
        (content, embedding, source_file, page, chunk_id)
        VALUES %s
        """,
        rows,
        template="(%s, %s, %s, %s, %s)",
    )

    conn.commit()

    cur.close()
    conn.close()

    print(f"{len(rows)} chunk pgvector'a yazıldı.")



def similarity_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Verilen soruyu embed edip bütün chunk'ların
    cosine distance değerini hesaplar.

    En küçük distance = en benzer chunk.
    """

    query_embedding = Vector(embed_texts([query])[0])

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            content,
            source_file,
            page,
            chunk_id,
            embedding <=> %s AS distance
        FROM document_chunks
        """,
        (query_embedding,)
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    results = []

    for content, source_file, page, chunk_id, distance in rows:
        results.append({
            "content": content,
            "source_file": source_file,
            "page": page,
            "chunk_id": chunk_id,
            "distance": distance,
        })

   
    results.sort(key=lambda x: x["distance"])

 
    return results[:top_k]
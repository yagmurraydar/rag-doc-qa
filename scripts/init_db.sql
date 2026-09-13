CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(384),  -- all-MiniLM-L6-v2 modeli 384 boyutlu vektör üretir
    source_file TEXT,
    page INTEGER,
    chunk_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Benzerlik aramasını hızlandırmak için index
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
    ON document_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
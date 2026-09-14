from pydantic import BaseModel


class UploadResponse(BaseModel):
    message: str
    file_name: str
    num_pages: int
    num_chunks: int


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class SourceInfo(BaseModel):
    source_file: str
    page: int


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
from pydantic import BaseModel


class KnowledgeChunk(BaseModel):
    chunk_id: str
    doc_name: str
    doc_type: str
    title: str
    text: str
    article_no: str | None = None
    article_label: str | None = None
    part_title: str | None = None
    chapter_title: str | None = None
    section_title: str | None = None
    source_path: str | None = None

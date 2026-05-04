from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    doc_id: str
    file_name: str
    file_type: str
    source_path: str
    title: str | None = None
    contract_type_hint: str | None = None
    party_a: str | None = None
    party_b: str | None = None
    signed_date: str | None = None
    page_count: int = 0


class DocumentSpan(BaseModel):
    span_id: str
    page_no: int | None = None
    block_index: int
    start_offset: int
    end_offset: int
    text: str


class ClauseChunk(BaseModel):
    chunk_id: str
    chunk_level: str
    clause_no: str | None = None
    parent_clause_no: str | None = None
    section_title: str
    page_no: int | None = None
    start_offset: int
    end_offset: int
    source_text: str
    prev_chunk_id: str | None = None
    next_chunk_id: str | None = None


class ParsedDocument(BaseModel):
    metadata: DocumentMetadata
    raw_text: str
    spans: list[DocumentSpan] = Field(default_factory=list)
    clause_chunks: list[ClauseChunk] = Field(default_factory=list)
    html_content: str = Field(default="", description="Rich HTML representation (for .docx files via mammoth)")


class ParseResponse(BaseModel):
    document: ParsedDocument

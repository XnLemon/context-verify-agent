from langchain_core.documents import Document

from app.schemas.document import ParsedDocument


def build_chunk_documents(parsed_document: ParsedDocument, contract_type: str) -> list[Document]:
    documents: list[Document] = []
    for chunk in parsed_document.clause_chunks:
        documents.append(
            Document(
                page_content=chunk.source_text,
                metadata={
                    "doc_id": parsed_document.metadata.doc_id,
                    "file_name": parsed_document.metadata.file_name,
                    "contract_type": contract_type,
                    "clause_no": chunk.clause_no,
                    "parent_clause_no": chunk.parent_clause_no,
                    "section_title": chunk.section_title,
                    "chunk_level": chunk.chunk_level,
                    "page_no": chunk.page_no,
                    "start_offset": chunk.start_offset,
                    "end_offset": chunk.end_offset,
                },
            )
        )
    return documents

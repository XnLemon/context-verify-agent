from langchain_core.documents import Document

from app.schemas.knowledge import KnowledgeChunk


def build_knowledge_documents(chunks: list[KnowledgeChunk]) -> list[Document]:
    documents: list[Document] = []
    for chunk in chunks:
        documents.append(
            Document(
                page_content=chunk.text,
                metadata={
                    "chunk_id": chunk.chunk_id,
                    "doc_name": chunk.doc_name,
                    "doc_type": chunk.doc_type,
                    "title": chunk.title,
                    "article_no": chunk.article_no,
                    "article_label": chunk.article_label,
                    "part_title": chunk.part_title,
                    "chapter_title": chunk.chapter_title,
                    "section_title": chunk.section_title,
                    "source_path": chunk.source_path,
                },
            )
        )
    return documents

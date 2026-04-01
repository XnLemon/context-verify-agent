from __future__ import annotations

import re

from app.schemas.document import ClauseChunk, DocumentSpan, ParsedDocument


class ContractChunker:
    def chunk(self, document: ParsedDocument) -> list[ClauseChunk]:
        chunks: list[ClauseChunk] = []
        current: dict | None = None
        parent_clause_no: str | None = None
        parent_title: str | None = None

        for span in document.spans:
            header = self._match_header(span.text)
            if header:
                if current:
                    chunks.append(self._to_chunk(current))
                level, clause_no, section_title = header
                if level == "clause":
                    parent_clause_no = clause_no
                    parent_title = section_title
                    current = self._new_chunk(span, level, clause_no, None, section_title)
                else:
                    title = section_title if section_title else (parent_title or clause_no)
                    current = self._new_chunk(span, level, clause_no, parent_clause_no, title)
                continue

            if current is None:
                current = self._new_chunk(span, "preface", None, None, "前言")
            else:
                current["source_text"] += "\n" + span.text
                current["end_offset"] = span.end_offset

        if current:
            chunks.append(self._to_chunk(current))

        self._link_neighbors(chunks)
        return self._split_long_chunks(chunks)

    def _match_header(self, text: str) -> tuple[str, str, str] | None:
        patterns = [
            (r"^(第[一二三四五六七八九十百零〇]+条)\s*(.*)$", "clause"),
            (r"^(\d+\.\d+(?:\.\d+)*)\s+(.*)$", "sub_clause"),
            (r"^(（[一二三四五六七八九十百零〇]+）)\s*(.*)$", "sub_item"),
            (r"^(\d+\.)\s*(.*)$", "sub_item"),
        ]
        for pattern, level in patterns:
            match = re.match(pattern, text)
            if match:
                clause_no = match.group(1).strip()
                title = (match.group(2) or clause_no).strip()
                return level, clause_no, title
        return None

    def _new_chunk(
        self,
        span: DocumentSpan,
        level: str,
        clause_no: str | None,
        parent_clause_no: str | None,
        section_title: str,
    ) -> dict:
        return {
            "chunk_id": f"chunk-{span.span_id}",
            "chunk_level": level,
            "clause_no": clause_no,
            "parent_clause_no": parent_clause_no,
            "section_title": section_title,
            "page_no": span.page_no,
            "start_offset": span.start_offset,
            "end_offset": span.end_offset,
            "source_text": span.text,
            "prev_chunk_id": None,
            "next_chunk_id": None,
        }

    def _to_chunk(self, payload: dict) -> ClauseChunk:
        return ClauseChunk(**payload)

    def _link_neighbors(self, chunks: list[ClauseChunk]) -> None:
        for index, chunk in enumerate(chunks):
            if index > 0:
                chunk.prev_chunk_id = chunks[index - 1].chunk_id
            if index + 1 < len(chunks):
                chunk.next_chunk_id = chunks[index + 1].chunk_id

    def _split_long_chunks(self, chunks: list[ClauseChunk]) -> list[ClauseChunk]:
        refined: list[ClauseChunk] = []
        for chunk in chunks:
            if len(chunk.source_text) <= 1200:
                refined.append(chunk)
                continue

            parts = self._split_by_sentences(chunk.source_text, max_chars=500)
            for index, part in enumerate(parts, start=1):
                refined.append(
                    ClauseChunk(
                        chunk_id=f"{chunk.chunk_id}-part{index}",
                        chunk_level="sentence_group",
                        clause_no=chunk.clause_no,
                        parent_clause_no=chunk.parent_clause_no or chunk.clause_no,
                        section_title=chunk.section_title,
                        page_no=chunk.page_no,
                        start_offset=chunk.start_offset,
                        end_offset=chunk.end_offset,
                        source_text=part,
                    )
                )

        self._link_neighbors(refined)
        return refined

    def _split_by_sentences(self, text: str, max_chars: int) -> list[str]:
        sentences = re.split(r"(?<=[。；;])", text)
        parts: list[str] = []
        current = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(current) + len(sentence) <= max_chars:
                current += sentence
            else:
                if current:
                    parts.append(current)
                current = sentence
        if current:
            parts.append(current)
        return parts or [text]

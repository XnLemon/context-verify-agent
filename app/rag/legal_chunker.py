from __future__ import annotations

import hashlib
import re
from pathlib import Path

from app.schemas.knowledge import KnowledgeChunk


class LegalKnowledgeChunker:
    PART_PATTERN = re.compile(r"^\s*第([一二三四五六七八九十百千万零〇]+)编[\s　]*(.+)?$")
    CHAPTER_PATTERN = re.compile(r"^\s*第([一二三四五六七八九十百千万零〇]+)章[\s　]*(.+)?$")
    SECTION_PATTERN = re.compile(r"^\s*第([一二三四五六七八九十百千万零〇]+)节[\s　]*(.+)?$")
    ARTICLE_PATTERN = re.compile(r"^\s*第([一二三四五六七八九十百千万零〇]+)条[\s　]*(.*)$")

    def chunk_file(self, file_path: str) -> list[KnowledgeChunk]:
        path = Path(file_path).expanduser().resolve()
        text = path.read_text(encoding="utf-8")
        return self.chunk_text(text=text, doc_name=path.name, source_path=str(path))

    def chunk_text(self, text: str, doc_name: str, source_path: str | None = None) -> list[KnowledgeChunk]:
        lines = [self._normalize_line(line) for line in text.splitlines()]
        chunks: list[KnowledgeChunk] = []
        context = {"part_title": None, "chapter_title": None, "section_title": None}
        current_article: dict | None = None

        for line in lines:
            if not line:
                continue

            part_match = self.PART_PATTERN.match(line)
            if part_match:
                context["part_title"] = self._build_heading("编", part_match.group(1), part_match.group(2))
                context["chapter_title"] = None
                context["section_title"] = None
                continue

            chapter_match = self.CHAPTER_PATTERN.match(line)
            if chapter_match:
                context["chapter_title"] = self._build_heading("章", chapter_match.group(1), chapter_match.group(2))
                context["section_title"] = None
                continue

            section_match = self.SECTION_PATTERN.match(line)
            if section_match:
                context["section_title"] = self._build_heading("节", section_match.group(1), section_match.group(2))
                continue

            article_match = self.ARTICLE_PATTERN.match(line)
            if article_match:
                if current_article:
                    chunks.append(self._build_chunk(current_article, doc_name, source_path))

                article_no = article_match.group(1)
                article_body = article_match.group(2).strip()
                current_article = {
                    "article_no": article_no,
                    "article_label": f"第{article_no}条",
                    "article_body_lines": [line if article_body else f"第{article_no}条"],
                    "part_title": context["part_title"],
                    "chapter_title": context["chapter_title"],
                    "section_title": context["section_title"],
                }
                continue

            if current_article:
                current_article["article_body_lines"].append(line)

        if current_article:
            chunks.append(self._build_chunk(current_article, doc_name, source_path))

        return chunks

    def _build_heading(self, level: str, ordinal: str, title: str | None) -> str:
        suffix = title.strip() if title else ""
        return f"第{ordinal}{level} {suffix}".strip()

    def _build_chunk(self, article: dict, doc_name: str, source_path: str | None) -> KnowledgeChunk:
        title_parts = [
            article.get("part_title"),
            article.get("chapter_title"),
            article.get("section_title"),
            article.get("article_label"),
        ]
        title = " / ".join(part for part in title_parts if part)
        text = "\n".join(article["article_body_lines"]).strip()

        return KnowledgeChunk(
            chunk_id=self._chunk_id(doc_name, article["article_label"], text),
            doc_name=doc_name,
            doc_type="law",
            title=title,
            text=text,
            article_no=article["article_no"],
            article_label=article["article_label"],
            part_title=article.get("part_title"),
            chapter_title=article.get("chapter_title"),
            section_title=article.get("section_title"),
            source_path=source_path,
        )

    def _normalize_line(self, line: str) -> str:
        return line.replace("\u3000", " ").strip()

    def _chunk_id(self, doc_name: str, article_label: str, text: str) -> str:
        payload = f"{doc_name}|{article_label}|{text[:40]}"
        return f"law_{hashlib.md5(payload.encode('utf-8')).hexdigest()[:12]}"

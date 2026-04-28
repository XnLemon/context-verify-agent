from __future__ import annotations

import re

from app.core.config import settings
from app.llm.client import get_chat_model
from app.llm.prompts import contract_redraft_chunk_prompt, contract_redraft_prompt


class ContractEditor:
    _CLAUSE_TITLE_RE = re.compile(r"^第[一二三四五六七八九十百零]+条")

    def __init__(self) -> None:
        self.llm = get_chat_model()

    def redraft_contract(
        self,
        *,
        contract_text: str,
        contract_type: str,
        our_side: str,
        accepted_issues: list[dict[str, str]],
    ) -> str:
        issue_text = self._format_accepted_issues(accepted_issues)
        max_chunk_chars = max(2000, settings.max_redraft_chunk_chars)

        if len(contract_text) <= max_chunk_chars:
            revised = self._invoke_full_redraft(
                contract_text=contract_text,
                contract_type=contract_type,
                our_side=our_side,
                issue_text=issue_text,
            )
            if revised:
                return revised
            raise RuntimeError("LLM 未返回可用的合同修订稿。")

        segments = self._build_segments(contract_text, max_chunk_chars)
        revised_segments: list[str] = []

        for segment in segments:
            related_issues = self._select_relevant_issues(segment, accepted_issues)
            if not related_issues:
                revised_segments.append(segment)
                continue

            revised = self._invoke_segment_redraft(
                contract_segment=segment,
                contract_type=contract_type,
                our_side=our_side,
                issue_text=self._format_accepted_issues(related_issues),
            )
            revised_segments.append(revised or segment)

        combined = "\n".join(part.strip("\n") for part in revised_segments if part is not None).strip()
        if not combined:
            raise RuntimeError("LLM 未返回可用的合同修订稿。")
        return combined

    def _invoke_full_redraft(self, *, contract_text: str, contract_type: str, our_side: str, issue_text: str) -> str:
        chain = contract_redraft_prompt | self.llm
        result = chain.invoke(
            {
                "contract_text": contract_text,
                "contract_type": contract_type,
                "our_side": our_side,
                "accepted_issues": issue_text,
            }
        )
        return (result.content or "").strip()

    def _invoke_segment_redraft(self, *, contract_segment: str, contract_type: str, our_side: str, issue_text: str) -> str:
        chain = contract_redraft_chunk_prompt | self.llm
        result = chain.invoke(
            {
                "contract_segment": contract_segment,
                "contract_type": contract_type,
                "our_side": our_side,
                "accepted_issues": issue_text,
            }
        )
        return (result.content or "").strip()

    def _format_accepted_issues(self, accepted_issues: list[dict[str, str]]) -> str:
        if not accepted_issues:
            return "无"
        lines: list[str] = []
        for index, issue in enumerate(accepted_issues, start=1):
            lines.append(
                f"{index}. 问题：{issue.get('message') or '未命名问题'}\n"
                f"   建议：{issue.get('suggestion') or '无'}\n"
                f"   位置：{issue.get('location') or '未标注'}"
            )
        return "\n".join(lines)

    def _build_segments(self, contract_text: str, max_chunk_chars: int) -> list[str]:
        blocks = self._split_contract_into_blocks(contract_text)
        segments: list[str] = []
        current_parts: list[str] = []
        current_len = 0

        for block in blocks:
            block_len = len(block)
            if block_len > max_chunk_chars:
                if current_parts:
                    segments.append("\n".join(current_parts).strip("\n"))
                    current_parts = []
                    current_len = 0
                segments.extend(self._split_oversized_block(block, max_chunk_chars))
                continue

            predicted = current_len + (1 if current_parts else 0) + block_len
            if predicted > max_chunk_chars and current_parts:
                segments.append("\n".join(current_parts).strip("\n"))
                current_parts = [block]
                current_len = block_len
            else:
                current_parts.append(block)
                current_len = predicted

        if current_parts:
            segments.append("\n".join(current_parts).strip("\n"))

        return [segment for segment in segments if segment.strip()]

    def _split_contract_into_blocks(self, contract_text: str) -> list[str]:
        lines = contract_text.splitlines()
        blocks: list[str] = []
        current: list[str] = []

        for line in lines:
            stripped = line.strip()
            if self._CLAUSE_TITLE_RE.match(stripped) and current:
                blocks.append("\n".join(current).strip("\n"))
                current = [line]
            else:
                current.append(line)

        if current:
            blocks.append("\n".join(current).strip("\n"))

        if not blocks:
            return [contract_text]
        return blocks

    def _split_oversized_block(self, block: str, max_chunk_chars: int) -> list[str]:
        paragraphs = [p for p in block.split("\n\n") if p.strip()]
        if not paragraphs:
            return [block]

        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            if len(paragraph) > max_chunk_chars:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(paragraph[i : i + max_chunk_chars] for i in range(0, len(paragraph), max_chunk_chars))
                continue

            candidate = paragraph if not current else f"{current}\n\n{paragraph}"
            if len(candidate) > max_chunk_chars and current:
                chunks.append(current)
                current = paragraph
            else:
                current = candidate

        if current:
            chunks.append(current)

        return chunks or [block]

    def _select_relevant_issues(self, segment: str, accepted_issues: list[dict[str, str]]) -> list[dict[str, str]]:
        related: list[dict[str, str]] = []
        for issue in accepted_issues:
            location = (issue.get("location") or "").strip()
            message = (issue.get("message") or "").strip()
            suggestion = (issue.get("suggestion") or "").strip()

            if not location and not message and not suggestion:
                related.append(issue)
                continue
            if location and location in segment:
                related.append(issue)
                continue
            if message and self._contains_keywords(segment, message):
                related.append(issue)
                continue
            if suggestion and self._contains_keywords(segment, suggestion):
                related.append(issue)

        return related

    def _contains_keywords(self, text: str, source: str) -> bool:
        keywords = [token for token in re.split(r"[，。；：、\s]+", source) if len(token) >= 3]
        return any(keyword in text for keyword in keywords)

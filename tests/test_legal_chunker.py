import unittest

from app.rag.legal_chunker import LegalKnowledgeChunker


LAW_TEXT = """第一编 总则
第一章 基本规定
第一条 为了保护民事主体的合法权益，调整民事关系，制定本法。
第二条 民法调整平等主体之间的人身关系和财产关系。
第二章 自然人
第一节 民事权利能力和民事行为能力
第三条 民事主体的人身权利、财产权利以及其他合法权益受法律保护。"""


class LegalChunkerTests(unittest.TestCase):
    def test_split_law_by_article(self) -> None:
        chunks = LegalKnowledgeChunker().chunk_text(LAW_TEXT, doc_name="民法典.TXT")

        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0].article_label, "第一条")
        self.assertEqual(chunks[0].chapter_title, "第一章 基本规定")
        self.assertEqual(chunks[1].article_label, "第二条")
        self.assertEqual(chunks[2].section_title, "第一节 民事权利能力和民事行为能力")
        self.assertIn("第三条", chunks[2].text)


if __name__ == "__main__":
    unittest.main()

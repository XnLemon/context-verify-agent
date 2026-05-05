import unittest

from langchain_core.documents import Document

from app.core.config import settings
from app.rag.reranker import QwenReranker
from app.rag.retriever import ContractKnowledgeRetriever


class FakeVectorStore:
    def __init__(self, docs: list[Document]) -> None:
        self.docs = docs
        self.last_k = None

    def similarity_search(self, query: str, k: int = 3) -> list[Document]:
        self.last_k = k
        return self.docs[:k]


class StubReranker:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def rerank(self, query: str, documents: list[Document], top_k: int) -> list[Document]:
        self.calls += 1
        if self.fail:
            raise RuntimeError("rerank failed")
        ranked = list(reversed(documents))
        return ranked[:top_k]


class RerankerTests(unittest.TestCase):
    def test_qwen_reranker_reorders_by_score(self) -> None:
        docs = [
            Document(page_content="d0"),
            Document(page_content="d1"),
            Document(page_content="d2"),
        ]
        reranker = QwenReranker()
        reranker._request_with_retry = lambda payload: {
            "output": {
                "results": [
                    {"index": 1, "relevance_score": 0.9},
                    {"index": 2, "relevance_score": 0.5},
                    {"index": 0, "relevance_score": 0.1},
                ]
            }
        }

        out = reranker.rerank("query", docs, top_k=2)

        self.assertEqual([item.page_content for item in out], ["d1", "d2"])

    def test_retriever_skips_rerank_when_dense_and_bm25_top1_agree(self) -> None:
        docs = [
            Document(page_content="dispute resolution jurisdiction court"),
            Document(page_content="payment terms liquidated damages"),
            Document(page_content="delivery acceptance contract purpose"),
            Document(page_content="confidentiality information disclosure"),
        ]
        vector = FakeVectorStore(docs)
        reranker = StubReranker(fail=False)
        retriever = ContractKnowledgeRetriever(vector_store=vector, reranker=reranker)

        old_enable_hybrid = settings.retrieval_enable_hybrid
        old_dense_pool_k = settings.retrieval_dense_pool_k
        try:
            settings.retrieval_enable_hybrid = True
            settings.retrieval_dense_pool_k = 4

            out = retriever.retrieve_documents_with_rerank(
                query="dispute resolution jurisdiction court",
                fetch_k=3,
                final_k=2,
                use_rerank=True,
            )
        finally:
            settings.retrieval_enable_hybrid = old_enable_hybrid
            settings.retrieval_dense_pool_k = old_dense_pool_k

        self.assertEqual(out, docs[:2])
        self.assertEqual(reranker.calls, 0)
        self.assertEqual(retriever.last_rerank_meta.get("reason"), "short_circuit_dense_bm25_top1_agree")

    def test_retriever_fallback_to_vector_when_rerank_fails(self) -> None:
        docs = [Document(page_content="a"), Document(page_content="b"), Document(page_content="c")]
        vector = FakeVectorStore(docs)
        reranker = StubReranker(fail=True)
        retriever = ContractKnowledgeRetriever(vector_store=vector, reranker=reranker)

        out = retriever.retrieve_documents_with_rerank(
            query="q",
            fetch_k=3,
            final_k=2,
            use_rerank=True,
        )

        self.assertEqual([item.page_content for item in out], ["a", "b"])
        self.assertEqual(vector.last_k, 36)
        self.assertEqual(reranker.calls, 1)

    def test_retriever_can_disable_rerank(self) -> None:
        docs = [Document(page_content="a"), Document(page_content="b"), Document(page_content="c")]
        vector = FakeVectorStore(docs)
        reranker = StubReranker(fail=False)
        retriever = ContractKnowledgeRetriever(vector_store=vector, reranker=reranker)

        out = retriever.retrieve_documents_with_rerank(
            query="q",
            fetch_k=3,
            final_k=2,
            use_rerank=False,
        )

        self.assertEqual([item.page_content for item in out], ["a", "b"])
        self.assertEqual(reranker.calls, 0)

    def test_hybrid_can_pull_relevant_doc_from_larger_dense_pool(self) -> None:
        docs = [
            Document(page_content="payment terms liquidated damages"),
            Document(page_content="delivery acceptance contract purpose"),
            Document(page_content="confidentiality information disclosure"),
            Document(page_content="dispute resolution jurisdiction court"),
            Document(page_content="appendix effective date"),
        ]
        vector = FakeVectorStore(docs)
        retriever = ContractKnowledgeRetriever(vector_store=vector, reranker=StubReranker(fail=False))

        old_enable_hybrid = settings.retrieval_enable_hybrid
        old_dense_pool_k = settings.retrieval_dense_pool_k
        try:
            settings.retrieval_enable_hybrid = True
            settings.retrieval_dense_pool_k = 5

            out = retriever.retrieve_documents_with_rerank(
                query="dispute resolution jurisdiction court",
                fetch_k=3,
                final_k=3,
                use_rerank=False,
            )
        finally:
            settings.retrieval_enable_hybrid = old_enable_hybrid
            settings.retrieval_dense_pool_k = old_dense_pool_k

        contents = [item.page_content for item in out]
        self.assertTrue(any("dispute resolution" in content for content in contents))
        self.assertEqual(vector.last_k, 5)


if __name__ == "__main__":
    unittest.main()

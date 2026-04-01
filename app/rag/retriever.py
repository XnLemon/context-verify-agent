from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


class ContractKnowledgeRetriever:
    def __init__(self, vector_store: FAISS) -> None:
        self.vector_store = vector_store

    def retrieve_documents(self, query: str, k: int = 3) -> list[Document]:
        return self.vector_store.similarity_search(query, k=k)

    def retrieve(self, query: str, k: int = 3) -> list[str]:
        docs = self.retrieve_documents(query, k=k)
        return [doc.page_content for doc in docs]

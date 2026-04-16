import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Contract Review Agent"
    default_contract_type: str = "采购合同"
    qwen_api_key: str | None = os.getenv("QWEN_API_KEY")
    qwen_base_url: str = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    langchain_model: str = os.getenv("QWEN_CHAT_MODEL", "qwen-max")
    langchain_embedding_model: str = os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v4")
    vector_backend: str = os.getenv("VECTOR_BACKEND", "milvus")
    knowledge_vector_store_dir: str = "knowledge/ingested/laws_faiss"
    milvus_uri: str = os.getenv("MILVUS_URI", "http://127.0.0.1:19530")
    milvus_collection_name: str = os.getenv("MILVUS_COLLECTION_NAME", "legal_knowledge_chunks")
    milvus_consistency_level: str = os.getenv("MILVUS_CONSISTENCY_LEVEL", "Session")
    retrieval_enable_rerank: bool = os.getenv("RETRIEVAL_ENABLE_RERANK", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    rerank_model: str = os.getenv("RERANK_MODEL", "qwen3-rerank")
    rerank_endpoint: str | None = os.getenv("RERANK_ENDPOINT")
    retrieval_fetch_k: int = int(os.getenv("RETRIEVAL_FETCH_K", "12"))
    retrieval_final_k: int = int(os.getenv("RETRIEVAL_FINAL_K", "4"))
    retrieval_enable_hybrid: bool = os.getenv("RETRIEVAL_ENABLE_HYBRID", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    retrieval_dense_pool_k: int = int(os.getenv("RETRIEVAL_DENSE_POOL_K", "36"))
    rerank_timeout_seconds: int = int(os.getenv("RERANK_TIMEOUT_SECONDS", "8"))
    rerank_max_retries: int = int(os.getenv("RERANK_MAX_RETRIES", "0"))
    react_max_steps: int = int(os.getenv("REACT_MAX_STEPS", "3"))
    postgres_dsn: str | None = os.getenv("POSTGRES_DSN", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/contract_agent")
    max_upload_size_bytes: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(5 * 1024 * 1024)))
    max_redraft_chunk_chars: int = int(os.getenv("MAX_REDRAFT_CHUNK_CHARS", "12000"))


settings = Settings()

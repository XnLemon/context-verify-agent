import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Contract Review Agent MVP"
    default_contract_type: str = "采购合同"
    qwen_api_key: str | None = os.getenv("QWEN_API_KEY")
    qwen_base_url: str = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    langchain_model: str = os.getenv("QWEN_CHAT_MODEL", "qwen-max")
    langchain_embedding_model: str = os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v4")
    knowledge_vector_store_dir: str = "knowledge/ingested/laws_faiss"
    max_upload_size_bytes: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(5 * 1024 * 1024)))


settings = Settings()

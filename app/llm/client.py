from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings


def get_chat_model() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.qwen_api_key,
        base_url=settings.qwen_base_url,
        model=settings.langchain_model,
        temperature=0,
    )


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        api_key=settings.qwen_api_key,
        base_url=settings.qwen_base_url,
        model=settings.langchain_embedding_model,
    )

from langchain_ollama import OllamaLLM
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from .prompt import SYSTEM_PROMPT
from .retriever import retrieve
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
MODEL_NAME = os.getenv("LLM_MODEL", "qwen2.5:14b")

NOT_FOUND_MESSAGE = "提供された文書には該当する情報が見つかりませんでした。"

def get_llm():
    return OllamaLLM(
        base_url=OLLAMA_URL,
        model=MODEL_NAME,
        temperature=0.1,  # 低めに設定してハルシネーション抑制
    )

def query(question: str) -> dict:
    docs = retrieve(question)

    if not docs:
        return {
            "answer": NOT_FOUND_MESSAGE,
            "sources": [],
        }

    # コンテキスト構築（出典付き）
    context_parts = []
    sources = []
    for doc in docs:
        meta = doc.metadata
        filename = meta.get("filename", "不明")
        page = meta.get("page", "")
        section = meta.get("section", "")

        label = filename
        if page:
            label += f" p.{page}"
        if section:
            label += f"「{section}」"

        context_parts.append(f"【出典: {label}】\n{doc.page_content}")
        sources.append({"filename": filename, "page": page, "section": section})

    context = "\n\n".join(context_parts)

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=SYSTEM_PROMPT,
    )
    chain = LLMChain(llm=get_llm(), prompt=prompt)
    answer = chain.run(context=context, question=question)

    return {
        "answer": answer.strip(),
        "sources": sources,
    }

# 社内文書 RAG システム

## 起動方法

### Mac（開発環境）
```bash
docker compose up --build
```

### Windowsサーバー（GPU環境）
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

## 初回セットアップ（Ollamaモデルのダウンロード）
```bash
docker compose exec ollama ollama pull qwen2.5:14b
```

## アクセス
- Streamlit UI: http://localhost:8501
- FastAPI: http://localhost:8080
- ChromaDB: http://localhost:8000

## ディレクトリ構成
```
rag-system/
├── api/          FastAPI（RAGロジック）
├── worker/       文書処理ワーカー
├── streamlit/    UI
├── volumes/      データ永続化（Git管理外）
│   ├── chroma/   ChromaDB
│   ├── uploads/  アップロードファイル
│   └── ollama/   LLMモデル
├── docker-compose.yml
└── docker-compose.gpu.yml  Windows GPU用
```

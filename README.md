# rag-system

外部にデータを一切送らない、フルセルフホストのRAG（Retrieval-Augmented Generation）システムです。社内文書のようにクラウドAPIに投げられないドキュメントを対象に、社内での実運用を経て作られました。

## なぜフルセルフホストなのか

一般的なRAG構築はOpenAI等の外部APIを前提にしていますが、それだと機密文書を扱えません。このプロジェクトはLLM推論（Ollama）・ベクトル検索（ChromaDB）・埋め込みモデルまで全てローカルで完結させ、ドキュメントの内容が外部に出ない構成にしています。

## アーキテクチャ

```
┌───────────┐    ┌─────────┐    ┌────────┐
│ Streamlit │───▶│   API   │───▶│ Ollama │ (LLM推論)
│    UI     │    │(FastAPI)│    └────────┘
└───────────┘    └────┬────┘    ┌────────┐
                       │────────▶│ Chroma │ (ベクトルDB)
                       ▼         └────────┘
                  ┌─────────┐         ▲
                  │  Redis  │         │
                  │ (キュー) │         │
                  └────┬────┘         │
                       ▼              │
                  ┌─────────┐         │
                  │ Worker  │─────────┘
                  │(文書処理)│
                  └─────────┘
```

- **api / worker を分離**: ドキュメントのパース・埋め込み生成は時間がかかるため、Redisキュー経由の非同期処理にして、アップロードAPIがブロックしないようにしています
- **CPU / GPU 切り替え可能**: `EMBEDDING_DEVICE` 環境変数で切り替え。開発機（CPU）と本番GPUサーバーを同じコードベースで動かせます

## 起動方法

### Mac（開発環境・CPU）
```bash
docker compose up --build
```

### Windowsサーバー（GPU環境）
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

### 初回セットアップ（Ollamaモデルのダウンロード）
```bash
docker compose exec ollama ollama pull qwen2.5:14b
```

> **Note:** `api` / `worker` はソースコードをボリュームマウントしておらず、ビルド時にイメージへコピーする方式です。コード変更後は `restart` ではなく `docker compose up -d --build <service>` でイメージを再ビルドしないと反映されません。

## 使い方

1. `http://localhost:8501` の Streamlit UI を開く
2. ドキュメント（PDF / Word / Excel）をアップロード（worker が非同期でパース・埋め込み・ChromaDBへの登録を行う）
3. 登録が終わったら、同じUIから質問を入力する
4. MMR検索＋コサイン類似度フィルタリングで関連チャンクを取得し、Ollama上のLLMが回答を生成

## アクセス先
- Streamlit UI: http://localhost:8501
- FastAPI: http://localhost:8080
- ChromaDB: http://localhost:8000

## 環境変数

| 変数 | デフォルト | 説明 |
|---|---|---|
| `LLM_MODEL` | `qwen2.5:14b` | Ollamaで動かす生成モデル |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | 埋め込みモデル（多言語対応、日本語文書向け） |
| `EMBEDDING_DEVICE` | `cpu` | 埋め込み処理のデバイス（`cpu` / `cuda`） |

## ディレクトリ構成
```
rag-system/
├── api/          FastAPI（RAGロジック）
├── worker/       文書処理ワーカー（Redisキューを監視、非同期でパース・埋め込み）
├── streamlit/    UI
├── volumes/      データ永続化（Git管理外）
│   ├── chroma/   ChromaDB
│   ├── uploads/  アップロードファイル
│   └── ollama/   LLMモデル
├── docker-compose.yml
└── docker-compose.gpu.yml  Windows GPU用
```

## ライセンス
MIT License. 詳細は [LICENSE](./LICENSE) を参照してください。

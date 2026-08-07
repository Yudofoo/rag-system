# rag-system

外部にデータを一切送らない、フルセルフホストのRAG（Retrieval-Augmented Generation）システムです。社内文書のようにクラウドAPIに投げられないドキュメントを扱うユースケースを想定し、個人開発として作りました。

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
- **Ollamaのモデルデータはnamed volume**: bind mount（`./volumes/...`）だとWindows/Docker Desktop環境でホストOS⇄WSL2間のファイルI/Oが遅く、9GBのモデルロードに3分以上かかり読み込み中に接続断でロード失敗することもあった。named volume（WSL2内のネイティブファイルシステムに保存）に切り替えたところ、同じモデルのロードが2.8秒まで短縮した
- **2段階検索（ベクトル検索 + リランキング）**: 一次検索はベクトル類似度で候補を広めに取得し、Cross-Encoder（`BAAI/bge-reranker-v2-m3`）で再採点して上位k件に絞る。ベクトル検索単体（bi-encoder）は精度が粗く、財務報告書のような専門文書だと的外れなチャンクが上位に来ることがあったが、リランキング導入で大幅に改善した
- **表のMarkdown化**: PDFの表をそのままテキスト抽出すると行・列の対応関係が失われる（例:「（単位：百万円）」だけが単独チャンクになるなど）。PyMuPDFの`find_tables()`で表領域を検出し、Markdownテーブル形式に変換してからチャンク化することで、数値とその見出しの対応を保持している

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
4. ベクトル検索で候補を広めに取得 → Cross-Encoderでリランキング → 上位チャンクをコンテキストにOllama上のLLMが回答を生成

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
| `RERANKER_MODEL` | `BAAI/bge-reranker-v2-m3` | リランキング用Cross-Encoderモデル |
| `RERANKER_DEVICE` | `cpu` | リランキング処理のデバイス（`cpu` / `cuda`） |

## ディレクトリ構成
```
rag-system/
├── api/          FastAPI（RAGロジック）
├── worker/       文書処理ワーカー（Redisキューを監視、非同期でパース・埋め込み）
├── streamlit/    UI
├── volumes/      データ永続化（Git管理外、Ollamaモデルは含まない）
│   ├── chroma/   ChromaDB
│   └── uploads/  アップロードファイル
├── docker-compose.yml
└── docker-compose.gpu.yml  Windows GPU用
```

Ollamaのモデルデータは `ollama_data`、埋め込み/リランキングモデル（HuggingFaceキャッシュ）は `hf_cache` というnamed volumeで管理（`docker volume ls` で確認可能）。どちらもコンテナ再作成時の再ダウンロードを防ぐため。

## ライセンス
MIT License. 詳細は [LICENSE](./LICENSE) を参照してください。

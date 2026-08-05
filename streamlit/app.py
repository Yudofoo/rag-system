import streamlit as st
import requests
import os
import time

API_URL = os.getenv("API_URL", "http://api:8080")

st.set_page_config(page_title="社内文書 RAG", page_icon="📄", layout="wide")
st.title("📄 社内文書 質問応答システム")

tab_chat, tab_upload, tab_docs = st.tabs(["💬 質問する", "📤 文書を追加", "📚 登録済み文書"])

# ── 質問タブ ──────────────────────────────────────────
with tab_chat:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("📎 出典"):
                    for s in msg["sources"]:
                        label = s.get("filename", "不明")
                        if s.get("page"):
                            label += f"  p.{s['page']}"
                        if s.get("section"):
                            label += f"  「{s['section']}」"
                        st.markdown(f"- {label}")

    if question := st.chat_input("質問を入力してください"):
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("検索・生成中..."):
                try:
                    res = requests.post(
                        f"{API_URL}/query",
                        json={"question": question},
                        timeout=120,
                    )
                    data = res.json()
                    answer = data.get("answer", "エラーが発生しました")
                    sources = data.get("sources", [])
                except Exception as e:
                    answer = f"APIエラー: {e}"
                    sources = []

            st.markdown(answer)
            if sources:
                with st.expander("📎 出典"):
                    for s in sources:
                        label = s.get("filename", "不明")
                        if s.get("page"):
                            label += f"  p.{s['page']}"
                        if s.get("section"):
                            label += f"  「{s['section']}」"
                        st.markdown(f"- {label}")

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources,
        })

# ── 文書アップロードタブ ──────────────────────────────
with tab_upload:
    st.subheader("文書をアップロード")
    st.caption("対応形式：PDF・Word（.docx）・Excel（.xlsx / .xls）")

    uploaded = st.file_uploader(
        "ファイルを選択またはドラッグ＆ドロップ",
        type=["pdf", "docx", "xlsx", "xls"],
        accept_multiple_files=True,
    )

    if uploaded and st.button("アップロード開始", type="primary"):
        for file in uploaded:
            with st.spinner(f"{file.name} を送信中..."):
                try:
                    res = requests.post(
                        f"{API_URL}/ingest",
                        files={"file": (file.name, file.getvalue(), file.type)},
                        timeout=30,
                    )
                    data = res.json()
                    job_id = data.get("job_id")
                    st.info(f"✅ {file.name} をキューに追加しました")

                    # 処理完了まで待機
                    progress = st.progress(0, text="処理中...")
                    for i in range(60):
                        time.sleep(2)
                        status_res = requests.get(f"{API_URL}/status/{job_id}", timeout=10)
                        status = status_res.json().get("status")
                        if status == "done":
                            progress.progress(100, text="完了！")
                            st.success(f"✅ {file.name} の登録が完了しました")
                            break
                        elif status == "error":
                            err = status_res.json().get("error", "不明なエラー")
                            st.error(f"❌ エラー: {err}")
                            break
                        progress.progress((i + 1) * 100 // 60, text="処理中...")
                    else:
                        st.warning("処理に時間がかかっています。しばらくお待ちください。")
                except Exception as e:
                    st.error(f"❌ 送信エラー: {e}")

# ── 登録済み文書タブ ──────────────────────────────────
with tab_docs:
    st.subheader("登録済み文書一覧")
    if st.button("更新"):
        st.rerun()
    try:
        res = requests.get(f"{API_URL}/documents", timeout=10)
        docs = res.json().get("documents", [])
        if docs:
            for doc in docs:
                st.markdown(f"- 📄 {doc}")
        else:
            st.info("まだ文書が登録されていません")
    except Exception as e:
        st.error(f"取得エラー: {e}")

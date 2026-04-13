"""
app.py

Streamlit UI for RepoSnipy-LLM.

Usage:
  cd /path/to/RepoSnipyLLM
  streamlit run app.py
"""

import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline import run_question
from src.questions import TASKS, get_question
from src.llm import SUPPORTED_PROVIDERS, PROVIDER_MODELS

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="RepoSnipy-LLM",
    page_icon="🔍",
    layout="wide",
)

# ── Styling ───────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@300;400;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2rem; font-weight: 600;
    letter-spacing: -0.02em; color: #0f172a; margin-bottom: 0.25rem;
}
.subtitle { color: #64748b; font-size: 0.95rem; margin-bottom: 2rem; }

.answer-box {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-left: 4px solid #3b82f6; border-radius: 8px;
    padding: 1.5rem; font-size: 0.95rem; line-height: 1.7;
    color: #1e293b; white-space: pre-wrap;
}
.handler-badge {
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: 0.75rem; font-weight: 600;
    font-family: 'JetBrains Mono', monospace; margin-left: 8px;
}
.badge-single  { background: #dbeafe; color: #1d4ed8; }
.badge-search  { background: #dcfce7; color: #15803d; }
.badge-similar { background: #fef3c7; color: #b45309; }
</style>
""",
            unsafe_allow_html=True)

# ── ES repo loader ────────────────────────────────────────────────────────────


@st.cache_data(show_spinner="Loading repository list from Elasticsearch...")
def load_repo_list() -> list[dict]:
    """
    Load all repos from ES once at startup.
    Returns list of {repo_id, category, label} dicts.
    """
    es = Elasticsearch(
        os.getenv("ES_URL", "http://localhost:9200"),
        api_key=os.getenv("ES_API_KEY"),
    )
    INDEX = "repositories_enriched_new"
    repos = []
    resp = es.search(
        index=INDEX,
        body={
            "query": {
                "match_all": {}
            },
            "_source": ["category"],
            "size": 1000,
        },
        scroll="2m",
    )
    scroll_id = resp["_scroll_id"]
    hits = resp["hits"]["hits"]
    while hits:
        for hit in hits:
            repo_id = hit["_id"]
            cats = hit["_source"].get("category") or []
            if isinstance(cats, str):
                cats = [cats]
            cat_str = ", ".join(cats) if cats else "Unknown"
            repos.append({
                "repo_id": repo_id,
                "category": cat_str,
                "label": f"{repo_id}  [{cat_str}]",
            })
        resp = es.scroll(scroll_id=scroll_id, scroll="2m")
        scroll_id = resp["_scroll_id"]
        hits = resp["hits"]["hits"]
    es.clear_scroll(scroll_id=scroll_id)
    repos.sort(key=lambda x: x["repo_id"].lower())
    return repos


# ── Header ────────────────────────────────────────────────────────────────────

st.markdown('<div class="main-title">🔍 RepoSnipy-LLM</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Question-Driven Semantic Search and Explanation over Software Repositories</div>',
            unsafe_allow_html=True)

# Load repo list once
repo_list = load_repo_list()
repo_labels = [r["label"] for r in repo_list]
label_to_id = {r["label"]: r["repo_id"] for r in repo_list}

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    provider = st.selectbox(
        "Provider",
        options=sorted(SUPPORTED_PROVIDERS),
        index=sorted(SUPPORTED_PROVIDERS).index("deepseek") if "deepseek" in SUPPORTED_PROVIDERS else 0,
    )

    model_options = PROVIDER_MODELS.get(provider, [])
    model_name = st.selectbox("Model", options=model_options) if model_options else st.text_input(
        "Model", placeholder="Enter model name")
    model = f"{provider}:{model_name}" if model_name else None

    st.divider()
    topk = st.slider("Top-K (for similar questions)", min_value=3, max_value=20, value=10)

    st.divider()
    logdir = st.text_input(
        "Log directory",
        value="logs/runs",
        placeholder="logs/runs",
    )
    logdir = logdir.strip() or "logs/runs"

    st.divider()
    st.markdown("**Handler types:**")
    st.markdown("🔵 `single` — one repository")
    st.markdown("🟢 `search` — two+ repositories")
    st.markdown("🟡 `similar` — embedding search")

# ── Main layout ───────────────────────────────────────────────────────────────

col_left, col_right = st.columns([1, 2])

with col_left:
    st.markdown("### 📋 Select Question")

    task_options = {v["name"]: k for k, v in TASKS.items()}
    selected_task_name = st.selectbox("Task", options=list(task_options.keys()))
    task_id = task_options[selected_task_name]
    task = TASKS[task_id]

    questions = task["questions"]
    question_options = {f"Q{qid}: {q['name']}": qid for qid, q in questions.items()}
    selected_q_label = st.selectbox("Question", options=list(question_options.keys()))
    question_id = question_options[selected_q_label]
    question_config = get_question(task_id, question_id)
    handler = question_config["handler"]

    badge_class = {"single": "badge-single", "search": "badge-search", "similar": "badge-similar"}.get(handler, "")
    st.markdown(f"**Handler:** <span class='handler-badge {badge_class}'>{handler}</span>", unsafe_allow_html=True)
    st.caption(question_config["description"])

    st.divider()
    st.markdown("### 📦 Repository Input")

    repos = []

    if handler == "single" or handler == "similar":
        selected_label = st.selectbox(
            "Repository",
            options=repo_labels,
            index=None,
            placeholder="Search by name or category...",
        )
        if selected_label:
            repos = [label_to_id[selected_label]]

    elif handler == "search":
        # Initialise dynamic repo list in session state
        if "search_repos" not in st.session_state:
            st.session_state.search_repos = [None, None]

        for i, _ in enumerate(st.session_state.search_repos):
            selected = st.selectbox(
                f"Repository {i + 1}",
                options=repo_labels,
                index=None,
                placeholder="Search by name or category...",
                key=f"repo_{i}",
            )
            st.session_state.search_repos[i] = selected

        col_add, col_remove = st.columns(2)
        with col_add:
            if st.button("➕ Add repository", use_container_width=True):
                st.session_state.search_repos.append(None)
                st.rerun()
        with col_remove:
            if len(st.session_state.search_repos) > 2:
                if st.button("➖ Remove last", use_container_width=True):
                    st.session_state.search_repos.pop()
                    st.rerun()

        repos = [label_to_id[label] for label in st.session_state.search_repos if label is not None]

    # Validate
    if handler == "single" and len(repos) != 1:
        ready = False
    elif handler == "search" and len(repos) < 2:
        ready = False
    elif handler == "similar" and len(repos) != 1:
        ready = False
    else:
        ready = len(repos) > 0

    if handler == "search" and len(repos) < 2:
        st.warning("Please select at least 2 repositories.")

    run_btn = st.button(
        "🚀 Run",
        disabled=not ready or not model,
        use_container_width=True,
        type="primary",
    )

    if not model:
        st.warning("Please select a model.")

# ── Answer panel ──────────────────────────────────────────────────────────────

with col_right:
    st.markdown("### 💬 Answer")

    if run_btn and ready and model:
        with st.spinner(f"Running `{task_id}` Q{question_id} with `{model}`..."):
            try:
                prompt, answer, context = run_question(
                    question_config=question_config,
                    repos=repos,
                    model=model,
                    topk=topk,
                    logdir=logdir,
                    task_id=task_id,
                    question_id=question_id,
                )
                st.session_state["answer"] = answer
                st.session_state["context"] = context
                st.session_state["prompt"] = prompt
            except Exception as e:
                st.error(f"Error: {e}")
                st.session_state.pop("answer", None)

    if "answer" in st.session_state:
        st.markdown(st.session_state["answer"])

        with st.expander("🗂️ Retrieved Context"):
            st.code(st.session_state.get("context", ""), language=None)

        with st.expander("📝 Prompt"):
            st.code(st.session_state.get("prompt", ""), language=None)
    else:
        st.info("Configure your question on the left and click **Run** to see the answer.")

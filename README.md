# RepoSnipy-LLM

**Question-Driven Semantic Search and Explanation over Software Repositories**

RepoSnipy-LLM extends [RepoSnipy](https://github.com/RepoMining/RepoSnipy) with Retrieval-Augmented Generation (RAG), enabling developers and researchers to ask structured natural-language questions about Python repositories and receive grounded, evidence-backed answers.

---

## Overview

Rather than returning a plain ranked list of similar repositories, RepoSnipy-LLM lets you ask meaningful questions such as:

- *What does this repository do?*
- *Which repositories are designed as reusable libraries?*
- *Which repositories include automated tests?*
- *Find repositories most similar to this one.*

All answers are grounded in structured repository knowledge extracted by [inspect4py](https://github.com/SoftwareUnderstanding/inspect4py) and stored in Elasticsearch, ensuring traceability and reproducibility.

---

## Features

- **18 structured questions** across 5 task categories
- **Three handler types**: single-repo analysis, multi-repo comparison, and embedding-based similarity search
- **Two-stage RAG pipeline**: embedding retrieval (Stage A) + LLM generation (Stage B)
- **Multiple LLM backends**: DeepSeek, ZhipuAI, Ollama
- **Streamlit UI** for interactive use
- **CLI** for scripted and reproducible experiments
- **Full logging** of prompts, contexts, and answers

---

## Task Categories & Questions

| Task | # | Question | Handler |
|------|---|----------|---------|
| **Repository Understanding** | Q1 | What does this repository do? | single |
| | Q2 | What are the similarities and differences between repositories? | search |
| | Q3 | Find repositories similar to a given one | similar |
| **Architecture** | Q1 | Which repositories are organised into clearly separated modules? | search |
| | Q2 | Which repositories show a layered structure? | search |
| | Q3 | Which repositories are designed as reusable libraries? | search |
| | Q4 | Which repositories primarily consist of scripts? | search |
| **Execution** | Q1 | Which repositories provide a clear entry point? | search |
| | Q2 | Which repositories are designed for batch execution? | search |
| | Q3 | Which repositories rely on configuration files? | search |
| **Implementation** | Q1 | How does this repository read input data? | single |
| | Q2 | Which repositories rely heavily on external libraries? | search |
| | Q3 | Which repositories include automated tests? | search |
| | Q4 | Which repositories provide structured documentation? | search |
| **Reuse** | Q1 | Which repositories appear easy to reuse or extend? | search |
| | Q2 | Which repositories show signs of high structural complexity? | search |
| | Q3 | Which repositories are most similar to a given one? | similar |
| | Q4 | Where is the core functionality implemented? | single |

---

## Architecture

```
User Query
    │
    ▼
┌─────────────┐
│   CLI / UI  │  cli.py / app.py
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Pipeline   │  pipeline.py
│  (Controller)│
│             │
│  Stage A:   │  Embedding cosine similarity → candidate repos
│  Stage B:   │  Structured context assembly from Elasticsearch
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Data Loader │  data_loader.py → Elasticsearch (repositories_enriched)
└─────────────┘
       │
       ▼
┌─────────────┐
│  Prompt     │  prompt_builder.py → task-specific prompt templates
│  Builder    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  LLM Client │  llm.py → DeepSeek / ZhipuAI / Ollama
└─────────────┘
```

---

## Installation

### Prerequisites

- Python 3.10+
- Elasticsearch 9.x (Docker recommended)
- inspect4py (for data preparation)
- A supported LLM API key (DeepSeek, ZhipuAI) or Ollama running locally

### Install dependencies

```bash
pip install -r requirements.txt
```

### Environment variables

Create a `.env` file in the project root:

```env
ES_URL=http://localhost:9200
ES_API_KEY=your_elasticsearch_api_key

DEEPSEEK_API_KEY=your_deepseek_api_key
ZHIPU_API_KEY=your_zhipu_api_key
```

---

## Data Preparation

The pipeline requires repositories to be indexed in Elasticsearch. Run the following scripts in order:

```bash
# 1. Fetch repository list from Awesome Python
python scripts/1_fetch_process_awesome-python.py

# 2. Clone and analyse repositories with inspect4py
python scripts/2_inspect4py_analyse_awesome-python.py

# 3. Index raw inspect4py output into Elasticsearch
python scripts/3_indexer_raw.py

# 4. Build the enriched index with structured fields
python scripts/5_indexer_processed.py

# 5. Generate UniXcoder embeddings and fill into ES
python scripts/7_generate_embeddings.py
python scripts/7_fill_embeddings.py
python scripts/11_fill_sub_embeddings.py

# 6. Generate README summaries (uses GLM-4.7-Flash free tier)
python scripts/8_fill_readme_summary.py

# 7. Fill category labels
python scripts/10_fill_categories.py

# 8. Prepare final evaluation dataset
python scripts/12_save_final_datasets.py
```

---

## Usage

### Streamlit UI

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

### CLI

```bash
# List all tasks
python -m src.cli --list-tasks

# List questions for a task
python -m src.cli --task repository_understanding --list-task-questions

# Single repository analysis
python -m src.cli \
  --task repository_understanding \
  --question 1 \
  --repo pallets/flask \
  --model deepseek:deepseek-chat

# Compare two repositories
python -m src.cli \
  --task repository_understanding \
  --question 2 \
  --repo pallets/flask django/django \
  --model deepseek:deepseek-chat

# Find similar repositories
python -m src.cli \
  --task repository_understanding \
  --question 3 \
  --repo pallets/flask \
  --topk 10 \
  --model deepseek:deepseek-chat

# Save logs for reproducibility
python -m src.cli \
  --task architecture \
  --question 1 \
  --repo pallets/flask django/django \
  --model deepseek:deepseek-chat \
  --logdir logs/my_experiment
```

### Supported models

| Provider | Format | Example models |
|----------|--------|----------------|
| DeepSeek | `deepseek:<model>` | `deepseek:deepseek-chat` |
| ZhipuAI | `zhipu:<model>` | `zhipu:glm-4.7-flash` |
| Ollama | `ollama:<model>` | `ollama:qwen3:8b` |

---

## Evaluation

### Stage A: Retrieval Evaluation

Compares six retrieval methods using Precision@K, Recall@K, F1@K, and NDCG@K:

```bash
cd evaluations
python eval_stage_a.py
```

Results saved to `evaluations/results/stage_a_*.csv`.

### RAGAS Evaluation

Evaluates generation quality (Faithfulness, Answer Relevancy, Context Precision):

```bash
cd evaluations

# Step 1: Collect (question, context, answer) triples
python collect_ragas_data.py --model deepseek:deepseek-chat

# Step 2: Run RAGAS evaluation
python eval_ragas.py
```

Results saved to `evaluations/results/ragas_*.csv`.

---

## Project Structure

```
RepoSnipy-LLM/
├── app.py                      # Streamlit UI
├── requirements.txt
├── .env                        # API keys (not committed)
│
├── src/
│   ├── cli.py                  # Command-line interface
│   ├── pipeline.py             # RAG pipeline controller
│   ├── data_loader.py          # Elasticsearch data loading
│   ├── prompt_builder.py       # Prompt construction
│   ├── questions.py            # Task and question registry
│   ├── llm.py                  # LLM client (DeepSeek/ZhipuAI/Ollama)
│   ├── logger.py               # Run logging
│   └── output.py               # CLI output formatting
│
├── prompts/                    # Task-specific prompt templates
│   ├── batch_summarise.txt
│   ├── repository_understanding_*.txt
│   ├── architecture_*.txt
│   ├── execution_*.txt
│   ├── implementation_*.txt
│   └── reuse_*.txt
│
├── scripts/                    # Data preparation pipeline
│   ├── 1_fetch_process_awesome-python.py
│   ├── 2_inspect4py_analyse_awesome-python.py
│   ├── 3_indexer_raw.py
│   ├── 5_indexer_processed.py
│   ├── 7_generate_embeddings.py
│   ├── 7_fill_embeddings.py
│   ├── 8_fill_readme_summary.py
│   ├── 9_fill_readme_file_summary.py
│   ├── 10_fill_categories.py
│   ├── 11_fill_sub_embeddings.py
│   └── 12_save_final_datasets.py
│
├── evaluations/
│   ├── config.py               # Evaluation configuration
│   ├── eval_stage_a.py         # Stage A retrieval evaluation
│   ├── collect_ragas_data.py   # RAGAS data collection
│   ├── eval_ragas.py           # RAGAS evaluation
│   └── results/                # Evaluation outputs
│
└── data/
    ├── awesome-python_data.json
    ├── AWESOME-PYTHON-REPOS.pkl
    └── AWESOME-PYTHON-REPOS_FINAL.pkl
```

---

## Dataset

The system uses **487 Python repositories** from the [Awesome Python](https://github.com/vinta/awesome-python) list (April 2026 snapshot), spanning 69 categories. Each repository is indexed in Elasticsearch with:

- Structured metadata from inspect4py (directory tree, software type, invocation, tests, dependencies)
- LLM-generated README summary
- UniXcoder embeddings: full repository (3,072-dim) and four sub-embeddings (768-dim each: code, documentation, requirements, README)
- Awesome Python category labels

---

## Acknowledgements

This project builds on:

- [RepoSim4Py](https://github.com/RepoMining/RepoSim4Py) — repository embedding pipeline
- [inspect4py](https://github.com/SoftwareUnderstanding/inspect4py) — static code analysis
- [UniXcoder](https://github.com/microsoft/CodeBERT/tree/master/UniXcoder) — code representation model
- [Awesome Python](https://github.com/vinta/awesome-python) — curated repository dataset
- [RAGAS](https://github.com/explodinggradients/ragas) — RAG evaluation framework

---

<!-- ## Citation

If you use RepoSnipy-LLM in your research, please cite:

```bibtex
@inproceedings{zhang2026reposnipy,
  title     = {RepoSnipy-LLM: Question-Driven Semantic Search and Explanation over Software Repositories},
  author    = {Zhang, Honglin and Filgueira, Rosa},
  booktitle = {Proceedings of the 22nd IEEE International Conference on eScience},
  year      = {2026}
}
```

--- -->

## License

MIT License
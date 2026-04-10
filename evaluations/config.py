"""
config.py

Central configuration for RepoSnipy-LLM evaluation.
All evaluation scripts import from this file to ensure consistency
and reproducibility across Stage A and RAGAS evaluations.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Elasticsearch ─────────────────────────────────────────────────────────────

ES_URL = os.getenv("ES_URL", "http://localhost:9200")
ES_API_KEY = os.getenv("ES_API_KEY")
INDEX = "repositories_enriched_new"

# ── Data paths ────────────────────────────────────────────────────────────────

PKL_PATH = "../data/AWESOME-PYTHON-REPOS_FINAL.pkl"

# ── Evaluation parameters ─────────────────────────────────────────────────────

# K values for Precision@K, Recall@K, F1@K, NDCG@K
K_VALUES = [5, 10]

# Minimum category size to be included in evaluation
MIN_CATEGORY_SIZE = 5

# Random seed used for reference repo selection (fixed for reproducibility)
RANDOM_SEED = 42

# ── Reference repositories (fixed, seed=42) ───────────────────────────────────
# One repo selected per category with size >= 5
REFERENCE_REPOS = [
    "pydantic/pydantic-ai",  # AI and Agents
    "jet-admin/jet-bridge",  # Admin Panels
    "grantjenks/python-sortedcontainers",  # Algorithms and Design Patterns
    "MagicStack/uvloop",  # Asynchronous Programming
    "Zulko/moviepy",  # Audio & Video Processing
    "django-guardian/django-guardian",  # Authentication
    "pyinvoke/invoke",  # Build Tools
    "Textualize/textual",  # CLI Development
    "httpie/cli",  # CLI Tools
    "PyCQA/isort",  # Code Analysis
    "dgunning/edgartools",  # Data Analysis
    "alecthomas/voluptuous",  # Data Validation
    "SciTools/cartopy",  # Data Visualization
    "patx/pickledb",  # Database
    "psycopg/psycopg",  # Database Drivers
    "inducer/pudb",  # Debugging Tools
    "Lightning-AI/pytorch-lightning",  # Deep Learning
    "getsentry/sentry-python",  # DevOps Tools
    "mpi4py/mpi4py",  # Distributed Computing
    "dashingsoft/pyarmor",  # Distribution
    "mkdocs/mkdocs",  # Documentation
    "docling-project/docling",  # File Format Processing
    "Suor/funcy",  # Functional Programming
    "r0x0r/pywebview",  # GUI Development
    "geopy/geopy",  # Geolocation
    "martinblech/xmltodict",  # HTML Manipulation
    "aio-libs/aiohttp",  # HTTP Clients
    "libvips/pyvips",  # Image Processing
    "python/cpython",  # Implementations
    "prompt-toolkit/python-prompt-toolkit",  # Interactive Interpreter
    "sartography/SpiffWorkflow",  # Job Schedulers
    "feature-engine/feature_engine",  # Machine Learning
    "BeanieODM/beanie",  # ORM
    "pypa/pip",  # Package Management
    "networkx/networkx",  # Science
    "joke2k/faker",  # Testing
    "sqids/sqids-python",  # Text Processing
    "sanic-org/sanic",  # Web APIs
    "Kludex/starlette",  # Web Frameworks
    "scrapy/scrapy",  # Web Scraping
    "benoitc/gunicorn",  # Web Servers
]

# Partner repo for each reference repo in search handler evaluation.
# Selected from the same category, seed=42, fixed for reproducibility.
SEARCH_PAIRS = {
    "pydantic/pydantic-ai": "TauricResearch/TradingAgents",
    "jet-admin/jet-bridge": "offerrall/FuncToWeb",
    "grantjenks/python-sortedcontainers": "pytransitions/transitions",
    "MagicStack/uvloop": "agronholm/anyio",
    "Zulko/moviepy": "sergree/matchering",
    "django-guardian/django-guardian": "authlib/authlib",
    "pyinvoke/invoke": "pydoit/doit",
    "Textualize/textual": "fastapi/typer",
    "httpie/cli": "tmux/tmux",
    "PyCQA/isort": "astral-sh/ty",
    "dgunning/edgartools": "pathwaycom/pathway",
    "alecthomas/voluptuous": "pyeve/cerberus",
    "SciTools/cartopy": "matplotlib/matplotlib",
    "patx/pickledb": "zopefoundation/ZODB",
    "psycopg/psycopg": "microsoft/mssql-python",
    "inducer/pudb": "ionelmc/python-manhole",
    "Lightning-AI/pytorch-lightning": "ChristosChristofidis/awesome-deep-learning",
    "getsentry/sentry-python": "boto/boto3",
    "mpi4py/mpi4py": "dask/dask",
    "dashingsoft/pyarmor": "pyinstaller/pyinstaller",
    "mkdocs/mkdocs": "mitmproxy/pdoc",
    "docling-project/docling": "yfedoseev/pdf_oxide",
    "Suor/funcy": "erikrose/more-itertools",
    "r0x0r/pywebview": "tomschimansky/customtkinter",
    "geopy/geopy": "geopandas/geopandas",
    "martinblech/xmltodict": "pallets/markupsafe",
    "aio-libs/aiohttp": "gruns/furl",
    "libvips/pyvips": "scikit-image/scikit-image",
    "python/cpython": "IronLanguages/ironpython3",
    "prompt-toolkit/python-prompt-toolkit": "tartley/colorama",
    "sartography/SpiffWorkflow": "agronholm/apscheduler",
    "feature-engine/feature_engine": "josephmisiti/awesome-machine-learning",
    "BeanieODM/beanie": "sqlalchemy/sqlalchemy",
    "pypa/pip": "python-poetry/poetry",
    "networkx/networkx": "statsmodels/statsmodels",
    "joke2k/faker": "HypothesisWorks/hypothesis",
    "sqids/sqids-python": "derek73/python-nameparser",
    "sanic-org/sanic": "spec-first/connexion",
    "Kludex/starlette": "miguelgrinberg/microdot",
    "scrapy/scrapy": "coleifer/micawber",
    "benoitc/gunicorn": "grpc/grpc",
}

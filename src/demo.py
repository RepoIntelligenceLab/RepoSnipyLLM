import asyncio
from typing import List

from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.runnables import chain

from utils.common_utils import CommonUtils

# 0. Load config
config = CommonUtils.get_sys_config()

# 1. Documents and Documents Loaders
file_path = "nke-10k-2023.pdf"
loader = PyPDFLoader(file_path)
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, add_start_index=True)
all_splits = text_splitter.split_documents(docs)

# 2. Embeddings
embeddings_model = OllamaEmbeddings(model=config["ollama"]["model"])
vector_1 = embeddings_model.embed_query(all_splits[0].page_content)
vector_2 = embeddings_model.embed_query(all_splits[1].page_content)
assert len(vector_1) == len(vector_2)

# 3. Vector stores
vector_store = InMemoryVectorStore(embedding=embeddings_model)
ids = vector_store.add_documents(documents=all_splits)


# 4. Retrievers
@chain
def retriever(query: str) -> List[Document]:
    return vector_store.similarity_search(query, k=1)


print(retriever.batch([
    "How many distribution centers does Nike have in the US?",
    "When was Nike incorporated?",
], ))

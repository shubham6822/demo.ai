"""Settings shared by ingest and the agent. Everything model-related comes from .env."""
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

STORE_DIR = Path(__file__).resolve().parent.parent / "store"
CHROMA_SUBDIR = "chroma"
COMPANY_FILE = "company.json"

LLM_MODEL = os.getenv("LLM_MODEL", "google_genai:gemini-3.5-flash-lite")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")


def embeddings():
    return GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)

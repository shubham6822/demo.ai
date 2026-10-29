"""Switch the agent to a company: load its PDF(s) into the vector store, replacing the previous company.

Usage: python -m app.ingest --company "Company X" path/to/file.pdf [more.pdf ...]
"""
import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.config import CHROMA_SUBDIR, COMPANY_FILE, STORE_DIR, embeddings


def ingest(company: str, pdfs: list[Path]) -> dict:
    for pdf in pdfs:
        if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
            sys.exit(f"Not a PDF file: {pdf}")

    pages = [
        Document(page.extract_text() or "", metadata={"source": pdf.name, "page": i + 1})
        for pdf in pdfs
        for i, page in enumerate(PdfReader(pdf).pages)
    ]
    chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80).split_documents(pages)
    if not chunks:
        sys.exit("No text found in the PDF(s). Scanned/image-only PDFs are not supported.")
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk"] = i  # reading order, so search can pull in a hit's neighbours

    # Build into a temp dir and swap at the end, so a failed run keeps the current company intact.
    STORE_DIR.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="store.tmp-", dir=STORE_DIR.parent))
    try:
        Chroma.from_documents(chunks, embeddings(), persist_directory=str(tmp / CHROMA_SUBDIR))
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    info = {
        "company": company,
        "files": [p.name for p in pdfs],
        "pages": len(pages),
        "chunks": len(chunks),
        "ingested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (tmp / COMPANY_FILE).write_text(json.dumps(info, indent=2))

    shutil.rmtree(STORE_DIR, ignore_errors=True)
    tmp.rename(STORE_DIR)
    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load a company's PDF(s) into the agent.")
    parser.add_argument("--company", required=True, help="Company name the agent will represent")
    parser.add_argument("pdfs", nargs="+", type=Path, help="One or more PDF files")
    args = parser.parse_args()

    info = ingest(args.company.strip(), args.pdfs)
    print(f"Agent is now the assistant for {info['company']}: "
          f"{len(info['files'])} file(s), {info['pages']} pages, {info['chunks']} chunks.")

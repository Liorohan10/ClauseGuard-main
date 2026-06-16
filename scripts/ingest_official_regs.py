import asyncio
import os
import sys
import re
import uuid
from pathlib import Path
from elasticsearch import Elasticsearch
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_elasticsearch import ElasticsearchStore
from langchain_core.embeddings import Embeddings

# Ensure the root of the project is in python path
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from clauseguard.config import settings
from clauseguard.services.pdf_service import PDFService
from clauseguard.services.embedding_service import EmbeddingService

class EmbeddingWrapper(Embeddings):
    """LangChain Embeddings wrapper around our custom EmbeddingService."""
    def __init__(self, service: EmbeddingService):
        self.service = service

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.service.encode_batch(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.service.encode(text)


def parse_document_hierarchical(text: str, filename: str) -> list[dict]:
    """
    Parses a regulatory document into Level 1 (Parent) divisions based on major headings.
    Returns a list of dicts with keys: title, summary, article_number, provision_type, full_hierarchy, text.
    """
    lines = text.split("\n")
    paragraphs = []
    curr_para = []
    
    # Clean and group lines into paragraphs
    for line in lines:
        if not line.strip():
            if curr_para:
                paragraphs.append("\n".join(curr_para))
                curr_para = []
        else:
            curr_para.append(line.strip())
    if curr_para:
        paragraphs.append("\n".join(curr_para))

    curr_chapter = ""
    curr_section = ""
    curr_division = ""
    curr_part = ""
    
    divisions = []
    curr_div_paras = []
    curr_div_meta = {}

    for para in paragraphs:
        # Check if the paragraph starts with a major heading
        ch_m = re.match(r"(?i)^Chapter\s+([IVXLCDM\d]+|[A-Z0-9]+)", para)
        sec_m = re.match(r"(?i)^Section\s+(\d+|[A-Z]+)", para)
        part_m = re.match(r"(?i)^Part\s+(\d+|[IVXLCDM\d]+)", para)
        div_m = re.match(r"(?i)^Division\s+(\d+|[IVXLCDM\d]+)", para)
        art_m = re.match(r"(?i)^Article\s+(\d+)", para)
        pr_m = re.match(r"(?i)^Principle\s+(\d+)", para)

        is_new_division = False
        new_meta = {}

        if ch_m:
            curr_chapter = para.split("\n")[0].strip()
        elif sec_m:
            curr_section = para.split("\n")[0].strip()
        elif part_m:
            curr_part = para.split("\n")[0].strip()
        elif div_m:
            curr_division = para.split("\n")[0].strip()
        elif art_m:
            is_new_division = True
            new_meta = {"type": "Art.", "num": art_m.group(1)}
        elif pr_m:
            is_new_division = True
            new_meta = {"type": "Principle", "num": pr_m.group(1)}

        if is_new_division:
            # Save previous division
            if curr_div_paras:
                divisions.append({
                    "text": "\n\n".join(curr_div_paras),
                    "meta": curr_div_meta.copy()
                })
            curr_div_paras = [para]
            
            # Construct hierarchy
            hierarchy_parts = []
            if curr_part: hierarchy_parts.append(curr_part)
            if curr_chapter: hierarchy_parts.append(curr_chapter)
            if curr_section: hierarchy_parts.append(curr_section)
            if curr_division: hierarchy_parts.append(curr_division)
            hierarchy_parts.append(para.split("\n")[0].strip())
            
            prefix = ""
            if "GDPR" in filename:
                prefix = "GDPR "
            elif "Privacy" in filename:
                prefix = "Australian Privacy Act "
            elif "EU" in filename:
                prefix = "EU Export Control "
            else:
                prefix = "Australian Export Control Act "

            art_num = f"{prefix}{new_meta['type']} {new_meta['num']}"
            lines_in_para = para.split("\n")
            provision_type = lines_in_para[1].strip() if len(lines_in_para) > 1 else lines_in_para[0].strip()
            
            curr_div_meta = {
                "article_number": art_num,
                "provision_type": provision_type,
                "full_hierarchy": " > ".join(hierarchy_parts),
                "title": lines_in_para[0].strip(),
                "summary": lines_in_para[1].strip() if len(lines_in_para) > 1 else ""
            }
        else:
            curr_div_paras.append(para)

    # Add the last division
    if curr_div_paras:
        divisions.append({
            "text": "\n\n".join(curr_div_paras),
            "meta": curr_div_meta.copy()
        })

    line_divisions = parse_document_hierarchical_by_lines(text, filename)
    if len(line_divisions) > len(divisions) * 2 and len(line_divisions) >= 20:
        return line_divisions

    # Fallback to paragraph splitting if no hierarchy is identified
    if not divisions or all(not d.get("meta") for d in divisions):
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=300)
        chunks = text_splitter.split_text(text)
        fallback_divisions = []
        for idx, chunk in enumerate(chunks):
            fallback_divisions.append({
                "text": chunk,
                "meta": {
                    "article_number": f"{filename.replace('.pdf', '')} Part {idx+1}",
                    "provision_type": "General Provisions",
                    "full_hierarchy": f"{filename.replace('.pdf', '')} > Part {idx+1}",
                    "title": f"Part {idx+1}",
                    "summary": chunk[:200].replace("\n", " ") + "..."
                }
            })
        return fallback_divisions

    # Clean empty/none metadata fields in valid divisions
    cleaned_divisions = []
    for d in divisions:
        if not d.get("meta"):
            d["meta"] = {
                "article_number": f"{filename.replace('.pdf', '')} General",
                "provision_type": "General Provisions",
                "full_hierarchy": f"{filename.replace('.pdf', '')} > General",
                "title": "General",
                "summary": "General rules and context."
            }
        cleaned_divisions.append(d)

    return cleaned_divisions


def parse_document_hierarchical_by_lines(text: str, filename: str) -> list[dict]:
    """Line-scanning parser for PDFs where Article/Section headings are split by extraction."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    divisions: list[dict] = []
    curr_lines: list[str] = []
    curr_meta: dict = {}
    curr_part = ""
    curr_chapter = ""
    curr_section = ""
    curr_division = ""

    def source_prefix() -> str:
        if "GDPR" in filename:
            return "GDPR "
        if "Privacy" in filename:
            return "Australian Privacy Act "
        if "EU" in filename:
            return "EU Export Control "
        return "Australian Export Control Act "

    def flush() -> None:
        if curr_lines and curr_meta:
            divisions.append({"text": "\n".join(curr_lines), "meta": curr_meta.copy()})

    for idx, line in enumerate(lines):
        part_m = re.match(r"(?i)^Part\s+([A-Z0-9IVXLCDM]+)\b", line)
        chapter_m = re.match(r"(?i)^Chapter\s+([A-Z0-9IVXLCDM]+)\b", line)
        section_heading_m = re.match(r"(?i)^Section\s+([A-Z0-9IVXLCDM]+)\b", line)
        division_m = re.match(r"(?i)^Division\s+([A-Z0-9IVXLCDM]+)\b", line)
        article_m = re.match(r"(?i)^Article\s+(\d+[A-Z]?)\s*(.*)$", line)
        section_m = re.match(r"(?i)^Section\s+(\d+[A-Z]?)\s*(.*)$", line)
        if article_m and article_m.group(2).lstrip().startswith(("(", ";", ",")):
            article_m = None
        if section_m and section_m.group(2).lstrip().startswith(("(", ";", ",")):
            section_m = None

        if part_m and not section_m:
            curr_part = line
        if chapter_m:
            curr_chapter = line
        if section_heading_m and not section_m:
            curr_section = line
        if division_m:
            curr_division = line

        parent_m = article_m or section_m
        if parent_m:
            flush()
            curr_lines = [line]
            label = "Art." if article_m else "Section"
            number = parent_m.group(1)
            inline_title = parent_m.group(2).strip()
            next_line = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
            title = inline_title or next_line
            hierarchy_parts = [
                part for part in [curr_part, curr_chapter, curr_section, curr_division, line]
                if part
            ]
            curr_meta = {
                "article_number": f"{source_prefix()}{label} {number}",
                "provision_type": title or line,
                "full_hierarchy": " > ".join(hierarchy_parts),
                "title": line,
                "summary": title or "Official legal provision.",
            }
            continue

        if curr_meta:
            curr_lines.append(line)

    flush()
    return divisions


def split_into_token_windows(text: str, min_tokens: int = 500, max_tokens: int = 800, overlap: int = 80) -> list[str]:
    """Split legal provisions into 500-800 token child chunks without dropping text."""
    tokens = re.findall(r"\S+", text)
    if not tokens:
        return []
    if len(tokens) <= max_tokens:
        return [text.strip()]

    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        if len(tokens) - end and end - start < min_tokens:
            end = min(start + min_tokens, len(tokens))
        chunks.append(" ".join(tokens[start:end]).strip())
        if end >= len(tokens):
            break
        start = max(0, end - overlap)
    return chunks


def ingest_pdfs():
    print("Starting official regulations ingestion pipeline...")
    
    # 1. Initialize services
    pdf_service = PDFService()
    embedding_service = EmbeddingService(settings.embedding_model)
    embeddings = EmbeddingWrapper(embedding_service)
    
    # 2. Setup Elasticsearch connection
    es_client = Elasticsearch(settings.elasticsearch_url)
    index_name = "clauseguard-official-regs"
    
    # Recreate the index to avoid stale entries
    if es_client.indices.exists(index=index_name):
        print(f"Deleting existing index: {index_name}")
        es_client.indices.delete(index=index_name)
    
    # Create the index with exact custom mappings for hierarchical retrieval
    es_client.indices.create(
        index=index_name,
        mappings={
            "properties": {
                "text": {"type": "text"},
                "vector": {
                    "type": "dense_vector",
                    "dims": 384,
                    "index": True,
                    "similarity": "cosine"
                },
                "metadata": {
                    "properties": {
                        "doc_id": {"type": "keyword"},
                        "parent_id": {"type": "keyword"},
                        "source_name": {"type": "keyword"},
                        "jurisdiction": {"type": "keyword"},
                        "domain": {"type": "keyword"},
                        "article_number": {"type": "keyword"},
                        "provision_type": {"type": "keyword"},
                        "full_hierarchy": {"type": "keyword"},
                        "parent_text": {"type": "text"},
                        "parent_title": {"type": "text"},
                        "parent_summary": {"type": "text"},
                        "child_text": {"type": "text"},
                        "child_idx": {"type": "integer"}
                    }
                }
            }
        }
    )
    
    # Initialize LangChain ElasticsearchStore
    vector_store = ElasticsearchStore(
        index_name=index_name,
        embedding=embeddings,
        client=es_client
    )
    
    # 3. Define the 4 PDFs to process
    workspace_root = Path(__file__).parent.parent.absolute()
    pdf_configs = [
        {
            "filename": "GDPR.pdf",
            "source_name": "Official GDPR Privacy Principles",
            "jurisdiction": "EU",
            "domain": "privacy"
        },
        {
            "filename": "Australian Privacy Act.pdf",
            "source_name": "Australian Privacy Act",
            "jurisdiction": "Australia",
            "domain": "privacy"
        },
        {
            "filename": "EU Export Control.pdf",
            "source_name": "EU Export Control Principles",
            "jurisdiction": "EU",
            "domain": "export"
        },
        {
            "filename": "Australia Export Control.pdf",
            "source_name": "Australian Export Control Act",
            "jurisdiction": "Australia",
            "domain": "export"
        }
    ]
    
    # 4. Ingest and split documents
    for config in pdf_configs:
        pdf_path = workspace_root / config["filename"]
        if not pdf_path.exists():
            print(f"ERROR: PDF file not found at {pdf_path}")
            continue
            
        print(f"Reading and parsing: {config['filename']}...")
        try:
            with open(pdf_path, "rb") as f:
                file_bytes = f.read()
            text, num_pages = pdf_service.parse(file_bytes, config["filename"])
            print(f"Parsed {num_pages} pages. Splitting into hierarchical divisions...")
            
            divisions = parse_document_hierarchical(text, config["filename"])
            print(f"Identified {len(divisions)} major divisions. Generating child chunks...")
            
            all_child_texts = []
            all_child_metadatas = []
            
            for d in divisions:
                parent_text = d["text"]
                meta = d["meta"]
                parent_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{config['filename']}::{meta['full_hierarchy']}::{meta['article_number']}"))
                
                # Split parent division into 500-800 token child chunks.
                child_chunks = split_into_token_windows(parent_text)
                
                for idx, chunk in enumerate(child_chunks):
                    # Prepend parent title and summary for context
                    header = (
                        f"Parent Article: {meta['title']}\n"
                        f"Provision Type: {meta['provision_type']}\n"
                        f"Hierarchy: {meta['full_hierarchy']}\n"
                        f"Summary: {meta['summary']}\n\n"
                    )
                    child_text = header + chunk
                    
                    child_meta = {
                        "doc_id": config["filename"],
                        "parent_id": parent_id,
                        "source_name": config["source_name"],
                        "jurisdiction": config["jurisdiction"],
                        "domain": config["domain"],
                        "article_number": meta["article_number"],
                        "provision_type": meta["provision_type"],
                        "full_hierarchy": meta["full_hierarchy"],
                        "parent_text": parent_text,
                        "parent_title": meta["title"],
                        "parent_summary": meta["summary"],
                        "child_text": chunk,
                        "child_idx": idx
                    }
                    
                    all_child_texts.append(child_text)
                    all_child_metadatas.append(child_meta)
            
            print(f"Generated {len(all_child_texts)} child chunks. Generating embeddings and indexing in batches of 20...")
            batch_size = 20
            import time
            for i in range(0, len(all_child_texts), batch_size):
                batch_texts = all_child_texts[i:i + batch_size]
                batch_metadatas = all_child_metadatas[i:i + batch_size]
                vector_store.add_texts(
                    texts=batch_texts,
                    metadatas=batch_metadatas
                )
                time.sleep(0.1)
            print(f"Ingested {config['source_name']} successfully.")
        except Exception as e:
            print(f"Exception during ingestion of {config['filename']}: {e}")
            
    print("Regulations ingestion pipeline complete.")

if __name__ == "__main__":
    ingest_pdfs()

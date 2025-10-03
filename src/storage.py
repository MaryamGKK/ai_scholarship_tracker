import os, logging, json
import chromadb
from chromadb.config import Settings
from src.embeddings import embedding_for_text

logger = logging.getLogger("scholarship-tracker.storage")

CHROMA_DIR = os.getenv("CHROMA_DB_DIR", "./chroma_db")

def init_chroma():
    client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=CHROMA_DIR))
    return client

def upsert_scholarship(client, doc_id, metadata):
    coll = client.get_or_create_collection("scholarships")
    text = metadata.get("title","") + "\n" + (metadata.get("eligibility") or "") + "\n" + (metadata.get("application_steps") or "") 
    emb = embedding_for_text(text)
    coll.upsert([(doc_id, emb, metadata)])

def search_similar(client, text, n=5):
    coll = client.get_or_create_collection("scholarships")
    emb = embedding_for_text(text)
    results = coll.query(query_embeddings=[emb], n_results=n)
    return results

import os, logging, requests, json
from typing import List
logger = logging.getLogger("scholarship-tracker.embeddings")

HF_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
HF_MODEL = os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")

def hf_inference_embedding(text: str, model: str=HF_MODEL) -> List[float]:
    if not HF_API_TOKEN:
        raise ValueError("HUGGINGFACE_API_TOKEN not set")
    url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}", "Content-Type": "application/json"}
    payload = {"inputs": text, "options": {"wait_for_model": True}}
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    # HF returns nested list for tokens or a single vector; collapse if necessary
    if isinstance(data, list) and len(data)>0 and isinstance(data[0], list):
        # some models return token vectors; average them
        import numpy as np
        arr = np.array(data)
        vec = list(arr.mean(axis=0))
        return vec
    return data

def embedding_for_text(text: str) -> List[float]:
    text = text[:10000]  # limit length
    try:
        if HF_API_TOKEN:
            return hf_inference_embedding(text)
    except Exception as e:
        logger.debug("HF inference failed: %s", e)
    # local fallback to sentence-transformers if available
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-mpnet-base-v2')
        vec = model.encode(text).tolist()
        return vec
    except Exception as e:
        logger.warning("Local sentence-transformers fallback failed: %s", e)
    # final fallback: dummy zero vector
    return [0.0]*384

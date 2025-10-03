# Upgrades Included

1. **Embeddings**: Uses Hugging Face Inference API (if HUGGINGFACE_API_TOKEN provided) to call a feature-extraction pipeline for sentence-transformers/all-mpnet-base-v2. If no token is available, falls back to local `sentence-transformers` model. This keeps everything usable within free tiers or fully local.

2. **Extraction improvements**: The extractor uses a few-shot prompt with strict JSON schema and validates/merges chunked responses. It will prefer null for uncertain booleans, and parse dates to ISO when possible.

3. **Reliability**: Added retry/backoff via `tenacity`, basic HTML cleanup heuristics, rate-limited search (retry decorator used), and better logging. Chroma upserts real embeddings now (or a zero vector fallback).

4. **Admin UI**: A Streamlit app (`src/admin_ui.py`) allows manual approval and exports `data/approved.json` that the main script can use when `ADMIN_REVIEW=true`.

5. **GitHub Actions**: Workflow file included for scheduled runs and artifact uploads.


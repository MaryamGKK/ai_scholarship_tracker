# AI Scholarship Tracker (Improved)

Automated system to find Masters scholarships in AI / ML / Quantum and email daily summaries.
This improved version includes:
- Real embeddings using Hugging Face Inference API (or local sentence-transformers fallback)
- Stronger Groq extraction prompt with few-shot examples and JSON validation/merging
- Retry/backoff utilities, rate limiting and HTML cleanup heuristics
- Simple Streamlit admin UI to review and approve scholarships before emailing
- GitHub Actions workflow for daily runs with artifact logs

See `config.example.env` and the `src/` folder for implementation details.

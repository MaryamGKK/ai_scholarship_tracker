import os, logging, textwrap, json, re
from typing import List, Dict, Any
from groq import Client
from bs4 import BeautifulSoup
from src.utils import normalize_text, parse_date_maybe, clean_html_text, retry_on_exception
from jsonschema import validate, ValidationError

logger = logging.getLogger("scholarship-tracker.extractor")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "gpt-4o-mini")

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": ["string", "null"]},
        "deadline": {"type": ["string", "null"]},
        "is_full_funding": {"type": ["boolean", "null"]},
        "is_masters_level": {"type": ["boolean", "null"]},
        "is_ai_related": {"type": ["boolean", "null"]},
        "open_to_egyptians": {"type": ["boolean", "null"]},
        "taught_in_english": {"type": ["boolean", "null"]},
        "eligibility": {"type": ["string", "null"]},
        "application_steps": {"type": ["string", "null"]}
    },
    "required": ["title","deadline","is_full_funding","is_masters_level","is_ai_related","open_to_egyptians","taught_in_english","eligibility","application_steps"]
}

EXTRACTION_PROMPT_TEMPLATE = """You are an assistant that extracts scholarship information from webpage text. Return STRICT JSON matching the schema described. Use exact keys: title, deadline, is_full_funding, is_masters_level, is_ai_related, open_to_egyptians, taught_in_english, eligibility, application_steps.

Example 1 input:
Text: "The Jane Doe Scholarship for MSc AI is fully funded (tuition + stipend). Open to international students including Egypt. Taught in English. Deadline: 30 June 2026. Apply via online form; need transcripts and CV."

Example 1 output (JSON):
{"title": "Jane Doe Scholarship for MSc AI", "deadline": "2026-06-30", "is_full_funding": true, "is_masters_level": true, "is_ai_related": true, "open_to_egyptians": true, "taught_in_english": true, "eligibility": "Transcripts, CV", "application_steps": "Apply via online form; submit transcripts and CV"}

Example 2 input:
Text: "Partial scholarships for master's students in computer science; not specific to AI; only EU citizens."

Example 2 output (JSON):
{"title": null, "deadline": null, "is_full_funding": false, "is_masters_level": true, "is_ai_related": false, "open_to_egyptians": false, "taught_in_english": null, "eligibility": null, "application_steps": null}

Now extract from the following text. If you are not sure about a boolean, prefer null. If date is present, return in ISO YYYY-MM-DD if possible, otherwise a short textual date.
Text:
"""

def init_groq_client(api_key=None):
    api_key = api_key or GROQ_API_KEY
    if not api_key:
        raise ValueError("GROQ_API_KEY is required for Groq inference")
    client = Client(api_key=api_key)
    return client

@retry_on_exception
def call_groq_for_json(client, text_chunk: str) -> Dict[str, Any]:
    prompt = EXTRACTION_PROMPT_TEMPLATE + text_chunk[:3000]
    try:
        resp = client.chat.completions.create(model=GROQ_MODEL, messages=[{"role":"user","content":prompt}], max_tokens=700)
        out_text = getattr(resp, "output", None) or getattr(resp, "text", None) or str(resp)
        # find JSON substring
        m = re.search(r"\{.*\}", out_text, re.S)
        if m:
            obj = json.loads(m.group(0))
            # validate schema loosely
            try:
                validate(instance=obj, schema=SCHEMA)
            except ValidationError:
                # attempt type coercion for booleans and strings
                for k in list(obj.keys()):
                    v = obj[k]
                    if isinstance(v, str) and v.lower() in ("true","false"):
                        obj[k] = True if v.lower()=="true" else False
                # final best-effort validate
            return obj
    except Exception as e:
        logger.debug("Groq call failed: %s", e)
    return {}

def extract_from_html(html: str, url: str, client: Client=None) -> Dict[str, Any]:
    client = client or init_groq_client()
    soup = BeautifulSoup(html, "lxml")
    text = clean_html_text(soup.get_text(separator="\n"))
    # heuristic: reduce boilerplate and repetitive nav text
    text = re.sub(r"(?i)cookie|privacy|terms|login|sign in|subscribe", "", text)
    chunks = [text[i:i+3000] for i in range(0, len(text), 3000)]
    merged = {"title": None, "deadline": None, "is_full_funding": None, "is_masters_level": None, "is_ai_related": None, "open_to_egyptians": None, "taught_in_english": None, "eligibility": None, "application_steps": None, "source": url}
    for c in chunks:
        obj = call_groq_for_json(client, c)
        if not obj:
            continue
        # merge fields preferring non-null and longer textual fields
        for k,v in obj.items():
            if k not in merged: continue
            if v in (None, "", []): continue
            # prefer longer eligibility/application text
            if k in ("eligibility","application_steps") and merged.get(k):
                if isinstance(v, str) and len(v) > len(merged.get(k)):
                    merged[k] = v.strip()
            else:
                merged[k] = v
    # try parse deadline
    if merged.get("deadline"):
        parsed = parse_date_maybe(merged["deadline"])
        if parsed:
            merged["deadline"] = parsed
    return merged

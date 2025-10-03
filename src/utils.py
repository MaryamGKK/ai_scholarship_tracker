import os, logging, re, time, json
from datetime import datetime
from dateutil import parser as dateparser
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

def setup_logging(level="INFO"):
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler("logs/tracker.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("scholarship-tracker")

def parse_date_maybe(text):
    try:
        dt = dateparser.parse(text, fuzzy=True, dayfirst=False)
        return dt.date().isoformat()
    except Exception:
        return None

def normalize_text(t):
    return re.sub(r"\s+", " ", (t or "").strip())

def clean_html_text(html_text):
    # remove extra whitespace and non-printables, keep newlines where helpful
    s = re.sub(r"\r", "", html_text)
    s = re.sub(r"\n{2,}", "\n", s)
    s = re.sub(r"\t+", " ", s)
    s = s.strip()
    return s

# Retry decorator for transient network/LLM calls
retry_on_exception = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception)
)

import os, time, logging, requests
from bs4 import BeautifulSoup
from typing import List, Dict
from urllib.parse import quote_plus
from src.utils import retry_on_exception

logger = logging.getLogger("scholarship-tracker.search")

SERPER_URL = "https://google.serper.dev/search"

@retry_on_exception
def serper_search(query, api_key, num=10):
    if not api_key:
        raise ValueError("No serper API key provided")
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": num}
    r = requests.post(SERPER_URL, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    results = []
    for item in data.get("results", []):
        results.append({"title": item.get("title"), "link": item.get("link")})
    return results

@retry_on_exception
def google_scrape(query, num=10):
    # Lightweight scraping of public search results - fragile and may be blocked.
    q = quote_plus(query)
    url = f"https://www.google.com/search?q={q}&num={num}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ScholarshipTracker/1.0)"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    results = []
    # different selectors for different Google page versions
    for g in soup.select(".kCrYT a, .yuRUbf a, a[href]"):
        href = g.get('href') or g.get('href')
        if not href:
            continue
        if href.startswith('/url?q='):
            link = href.split('/url?q=')[1].split('&')[0]
        elif href.startswith('http'):
            link = href
        else:
            continue
        title = g.get_text().strip() or link
        results.append({"title": title, "link": link})
    return results

# Seed sites to crawl directly
SEED_SITES = [
    "https://www.findamasters.com",
    "https://www.scholarshipportal.com",
    "https://www.topuniversities.com",
    "https://www.chevening.org",
    "https://www.fulbright.org",
]

@retry_on_exception
def crawl_seed_sites(limit=20):
    found = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ScholarshipTracker/1.0)"}
    for s in SEED_SITES:
        try:
            r = requests.get(s, headers=headers, timeout=20)
            r.raise_for_status()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if any(k in href.lower() for k in ["/scholarship", "masters", "funding", "bursary"]):
                    link = href if href.startswith("http") else requests.compat.urljoin(s, href)
                    found.append({"title": a.get_text().strip(), "link": link})
                    if len(found) >= limit:
                        break
        except Exception as e:
            logger.debug("failed to crawl %s: %s", s, e)
        if len(found) >= limit:
            break
    return found

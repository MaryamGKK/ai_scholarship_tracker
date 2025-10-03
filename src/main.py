import os, logging, time, hashlib, requests, json
from src.utils import setup_logging
from src import search, extractor, storage, notifier
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
logger = setup_logging(os.getenv("LOG_LEVEL", "INFO"))

def fetch_page(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; ScholarshipTracker/1.0)"}
        r = requests.get(url, headers=headers, timeout=25)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.debug("fetch failed %s %s", url, e)
        return None

def id_for(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()

def main():
    logger.info("Starting improved scholarship tracker run")
    queries = [
        "full scholarship masters AI machine learning quantum computing",
        "fully funded master's scholarships artificial intelligence",
        "masters scholarships for egyptian students ai",
    ]
    results = []
    serper_key = os.getenv("SERPER_API_KEY")
    for q in queries:
        try:
            if serper_key:
                res = search.serper_search(q, serper_key, num=10)
            else:
                res = search.google_scrape(q, num=10)
            results.extend(res)
        except Exception as e:
            logger.debug("search failed for '%s': %s", q, e)

    results.extend(search.crawl_seed_sites(limit=20))

    # dedupe
    seen = set()
    unique = []
    for r in results:
        l = r.get("link") or r.get("href")
        if not l: continue
        if l in seen: continue
        seen.add(l)
        unique.append(r)
    logger.info("Found %d unique candidate pages", len(unique))

    # init clients
    groq_client = None
    try:
        groq_client = extractor.init_groq_client()
    except Exception as e:
        logger.warning("Groq client not available: %s", e)

    chroma = None
    try:
        chroma = storage.init_chroma()
    except Exception as e:
        logger.warning("Chroma init failed: %s", e)

    candidates = []
    for r in unique[:60]:
        url = r.get("link")
        html = fetch_page(url)
        if not html: continue
        try:
            data = extractor.extract_from_html(html, url, client=groq_client)
            candidates.append(data)
            # store to DB regardless, to keep history
            if chroma and data.get('title'):
                try:
                    storage.upsert_scholarship(chroma, id_for(url), data)
                except Exception as e:
                    logger.debug("chroma upsert failed: %s", e)
        except Exception as e:
            logger.debug("extract failed for %s: %s", url, e)

    # save candidates for admin UI
    Path('data').mkdir(parents=True, exist_ok=True)
    with open('data/candidates.json','w',encoding='utf-8') as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)

    admin_review = os.getenv('ADMIN_REVIEW','false').lower()=='true'
    approved = []
    if admin_review:
        # if admin review is enabled, expect approved.json to be created by admin UI
        approved_path = Path('data/approved.json')
        if approved_path.exists():
            with open(approved_path,'r',encoding='utf-8') as f:
                approved = json.load(f).get('approved',[])
        else:
            logger.info('ADMIN_REVIEW enabled but data/approved.json not present; skipping email send.')
    else:
        # auto-filter for matches of interest
        for d in candidates:
            if d.get('is_masters_level') and d.get('is_ai_related') and d.get('open_to_egyptians') and d.get('taught_in_english'):
                approved.append(d)

    if approved:
        html = notifier.format_email_items(approved)
        try:
            notifier.send_email(f"Scholarship Tracker - {len(approved)} matches", html)
        except Exception as e:
            logger.error("Email send failed: %s", e)
    else:
        logger.info("No matching scholarships to notify today")

if __name__ == '__main__':
    main()

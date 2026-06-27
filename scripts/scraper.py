import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, date

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

ARCHVIZ_KEYWORDS = [
    "visualization", "visualisation", "archviz", "render", "rendering",
    "3d visual", "visual award",
]

def classify_type(title, desc):
    text = (title + " " + desc).lower()
    if any(k in text for k in ARCHVIZ_KEYWORDS):
        return "archviz"
    if any(k in text for k in ["student", "undergraduate", "graduate", "graduation"]):
        return "estudantil"
    return "conceito"

def parse_date(raw):
    raw = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", raw.strip())
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%d/%m/%Y")
        except ValueError:
            pass
    return raw

def scrape_page(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
        resp.raise_for_status()
    except Exception as e:
        print(f"  erro ao acessar {url}: {e}")
        return [], False

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    links = soup.find_all("a", href=re.compile(r"/competition/"))

    for a in links:
        text = a.get_text(" ", strip=True)
        href = a.get("href", "")
        if not href.startswith("http"):
            href = "https://competitions.archi" + href

        if "Submission:" not in text and "submission:" not in text:
            continue

        sub = re.search(r"Submission:\s*(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})", text, re.I)
        deadline = parse_date(sub.group(1)) if sub else ""

        reg = re.search(r"Registration:\s*(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})", text, re.I)
        registration = parse_date(reg.group(1)) if reg else ""

        prize_m = re.search(r"Prizes?:\s*(.+?)(?:\s+Type:)", text, re.I)
        prize = prize_m.group(1).strip() if prize_m else "Ver site"
        if not prize or "view" in prize.lower():
            prize = "Ver site"

        loc_m = re.search(r"Location:\s*(.+?)(?:\s+Language:)", text, re.I)
        location = loc_m.group(1).strip() if loc_m else "Concept"

        lang_m = re.search(r"Language:\s*(.+?)(?:\s+Prizes?:)", text, re.I)
        language = lang_m.group(1).strip() if lang_m else "English"

        title = re.split(r"\s+Submission:", text, flags=re.I)[0].strip()
        title = title[:120]

        desc_m = re.search(r"Type:\s*\S+\s+(.+)", text, re.DOTALL | re.I)
        desc = desc_m.group(1).strip()[:220] if desc_m else ""

        if not title or len(title) < 4:
            continue

        results.append({
            "title": title,
            "org": "competitions.archi",
            "type": classify_type(title, desc),
            "deadline": deadline,
            "registration": registration,
            "prize": prize,
            "location": location,
            "lang": language,
            "url": href,
            "desc": desc,
            "source": "competitions.archi",
        })

    next_link = soup.find("a", href=re.compile(r"/page/\d+/"))
    has_next = next_link is not None

    return results, has_next


def deduplicate(items):
    seen = set()
    out = []
    for item in items:
        key = item["title"].lower().strip()[:60]
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def filter_future(items):
    today = date.today()
    future = []
    for item in items:
        dl = item.get("deadline", "")
        if not dl:
            future.append(item)
            continue
        try:
            d, m, y = dl.split("/")
            if date(int(y), int(m), int(d)) >= today:
                future.append(item)
        except Exception:
            future.append(item)
    return future


def sort_by_deadline(items):
    def key(item):
        dl = item.get("deadline", "")
        try:
            d, m, y = dl.split("/")
            return date(int(y), int(m), int(d))
        except Exception:
            return date(9999, 1, 1)
    return sorted(items, key=key)


def main():
    print("=== Arch Competitions Scraper v2 ===")
    all_items = []

    base = "https://competitions.archi/submission-ending-soonest/"
    for page in range(1, 5):
        url = base if page == 1 else f"{base}page/{page}/"
        print(f"  página {page}...")
        items, has_next = scrape_page(url)
        all_items += items
        print(f"    {len(items)} encontrados")
        if not has_next:
            break

    all_items = deduplicate(all_items)
    all_items = filter_future(all_items)
    all_items = sort_by_deadline(all_items)

    output = {
        "updated_at": datetime.now(tz=__import__("datetime").timezone.utc).isoformat(),
        "count": len(all_items),
        "competitions": all_items,
    }

    with open("competitions.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nTotal: {len(all_items)} competições salvas.")
    for c in all_items[:8]:
        print(f"  {c['deadline']}  {c['title'][:60]}  [{c['prize']}]")


if __name__ == "__main__":
    main()

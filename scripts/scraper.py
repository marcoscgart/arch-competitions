import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, date

SOURCES = [
    {
        "name": "competitions.archi",
        "url": "https://competitions.archi/registration-ending-latest/",
        "origin": "competitions_archi",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ArchCompetitionsBot/1.0; "
        "+https://github.com/marcoscgart/arch-competitions)"
    )
}

ARCHVIZ_KEYWORDS = [
    "visualization", "visualisation", "archviz", "render", "rendering",
    "3d", "visual award", "architectural visualization",
]

CONCEPT_KEYWORDS = [
    "concept", "ideas", "unbuilt", "pavilion", "micro", "speculative",
    "housing", "living", "restaurant", "kiosk", "apartment", "cafe",
    "community", "park", "bridge", "tower", "urban", "landscape",
]


def classify_type(title: str, desc: str) -> str:
    text = (title + " " + desc).lower()
    if any(k in text for k in ARCHVIZ_KEYWORDS):
        return "archviz"
    if "student" in text or "undergraduate" in text or "graduate" in text:
        return "estudantil"
    if any(k in text for k in CONCEPT_KEYWORDS):
        return "conceito"
    return "open"


def parse_prize(text: str) -> str:
    text = text.strip()
    if not text or "view" in text.lower():
        return "Ver site"
    # normalise spacing
    text = re.sub(r"\s+", " ", text)
    return text


def parse_date_str(raw: str) -> str:
    """
    Tries to parse dates like '19th October 2026' → '19/10/2026'.
    Returns the original string on failure.
    """
    raw = raw.strip()
    raw = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", raw)
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%d/%m/%Y")
        except ValueError:
            pass
    return raw


def scrape_competitions_archi(url: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"[competitions.archi] request error: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # Each competition is wrapped in an <article> or a repeating block.
    # The site renders cards with class patterns; we look broadly.
    cards = soup.find_all("article")
    if not cards:
        # fallback: look for divs that contain both a date and a prize
        cards = soup.select("div.competition-item, div.comp-card, div[class*='competition']")

    if not cards:
        # Last resort: parse the raw text blocks between <hr> or similar separators
        print("[competitions.archi] no card elements found, trying text parse")
        return _text_fallback(soup)

    for card in cards:
        title_el = card.find(["h2", "h3", "h4", "a"])
        title = title_el.get_text(strip=True) if title_el else ""
        if not title or len(title) < 5:
            continue

        link_el = card.find("a", href=True)
        link = link_el["href"] if link_el else url
        if link and not link.startswith("http"):
            link = "https://competitions.archi" + link

        text = card.get_text(" ", strip=True)

        # Submission date
        sub_match = re.search(
            r"[Ss]ubmission[:\s]+(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})", text
        )
        deadline = parse_date_str(sub_match.group(1)) if sub_match else ""

        # Registration date
        reg_match = re.search(
            r"[Rr]egistration[:\s]+(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})", text
        )
        registration = parse_date_str(reg_match.group(1)) if reg_match else ""

        # Prize
        prize_match = re.search(
            r"[Pp]rize[s]?[:\s]+([^\n·•]+)", text
        )
        prize = parse_prize(prize_match.group(1)) if prize_match else "Ver site"

        # Location
        loc_match = re.search(r"[Ll]ocation[:\s]+([^\n·•]+)", text)
        location = loc_match.group(1).strip() if loc_match else "Concept"

        # Language
        lang_match = re.search(r"[Ll]anguage[:\s]+([^\n·•]+)", text)
        language = lang_match.group(1).strip() if lang_match else "English"

        # Description: first meaningful sentence
        desc_el = card.find("p")
        desc = desc_el.get_text(strip=True)[:220] if desc_el else text[:220]

        comp_type = classify_type(title, desc)

        results.append(
            {
                "title": title,
                "org": "competitions.archi",
                "type": comp_type,
                "deadline": deadline,
                "registration": registration,
                "prize": prize,
                "location": location,
                "lang": language,
                "url": link,
                "desc": desc,
                "source": "competitions.archi",
            }
        )

    return results


def _text_fallback(soup: BeautifulSoup) -> list[dict]:
    """Parse the page body as raw text when no card structure is found."""
    results = []
    body_text = soup.get_text("\n")
    # Split on lines that look like "Submission: DD Month YYYY"
    blocks = re.split(r"(?=Submission:\s+\d)", body_text)
    for block in blocks[1:]:  # skip preamble
        sub_match = re.search(
            r"Submission[:\s]+(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})", block
        )
        if not sub_match:
            continue
        deadline = parse_date_str(sub_match.group(1))

        prize_match = re.search(r"Prizes?[:\s]+([^\n]+)", block)
        prize = parse_prize(prize_match.group(1)) if prize_match else "Ver site"

        loc_match = re.search(r"Location[:\s]+([^\n]+)", block)
        location = loc_match.group(1).strip() if loc_match else "Concept"

        # Title: first non-empty line after the block header
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        title = lines[-1] if lines else "Sem título"
        # Remove trailing boilerplate
        title = title[:120]

        desc = " ".join(lines[: min(4, len(lines))])[:220]
        comp_type = classify_type(title, desc)

        results.append(
            {
                "title": title,
                "org": "competitions.archi",
                "type": comp_type,
                "deadline": deadline,
                "registration": "",
                "prize": prize,
                "location": location,
                "lang": "English",
                "url": "https://competitions.archi/registration-ending-latest/",
                "desc": desc,
                "source": "competitions.archi",
            }
        )
    return results


def scrape_buildner() -> list[dict]:
    url = "https://architecturecompetitions.com/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"[buildner] request error: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for card in soup.select("div.competition-card, article, div[class*='comp']"):
        title_el = card.find(["h2", "h3", "h4"])
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if len(title) < 5:
            continue

        link_el = card.find("a", href=True)
        link = link_el["href"] if link_el else url
        if link and not link.startswith("http"):
            link = "https://architecturecompetitions.com" + link

        text = card.get_text(" ", strip=True)

        prize_match = re.search(r"(\€|\$|USD|EUR)\s*[\d,\.]+", text)
        prize = prize_match.group(0).strip() if prize_match else "Ver site"

        date_match = re.search(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})", text)
        deadline = date_match.group(1) if date_match else ""

        desc_el = card.find("p")
        desc = desc_el.get_text(strip=True)[:220] if desc_el else text[:220]

        comp_type = classify_type(title, desc)

        results.append(
            {
                "title": title,
                "org": "Buildner",
                "type": comp_type,
                "deadline": deadline,
                "registration": "",
                "prize": prize,
                "location": "Concept",
                "lang": "English",
                "url": link,
                "desc": desc,
                "source": "buildner",
            }
        )

    return results


def deduplicate(items: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for item in items:
        key = item["title"].lower().strip()[:60]
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def filter_future(items: list[dict]) -> list[dict]:
    today = date.today()
    future = []
    for item in items:
        dl = item.get("deadline", "")
        if not dl:
            future.append(item)
            continue
        try:
            parts = dl.split("/")
            d = date(int(parts[2]), int(parts[1]), int(parts[0]))
            if d >= today:
                future.append(item)
        except Exception:
            future.append(item)
    return future


def main():
    print("=== Arch Competitions Scraper ===")
    all_items = []

    print("[1/2] Scraping competitions.archi...")
    all_items += scrape_competitions_archi(SOURCES[0]["url"])

    print("[2/2] Scraping Buildner...")
    all_items += scrape_buildner()

    all_items = deduplicate(all_items)
    all_items = filter_future(all_items)

    output = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(all_items),
        "competitions": all_items,
    }

    with open("competitions.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Done. {len(all_items)} competitions saved to competitions.json")


if __name__ == "__main__":
    main()

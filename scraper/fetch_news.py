"""
Fetch real news about threats in the oil & gas domain and drop them to data/news.json.
- Pure stdlib: urllib + xml.etree; no extra deps.
- Feeds: Google News queries plus a few security outlets.
"""

from __future__ import annotations

import email.utils
import html
import json
import ssl
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, List, Optional


FEEDS: List[Dict[str, str]] = [
    {
        "name": "Google News: oil gas cyber attack",
        "url": "https://news.google.com/rss/search?q=oil+gas+cyber+attack&hl=en&gl=US&ceid=US:en",
    },
    {
        "name": "Google News: pipeline incident fire explosion",
        "url": "https://news.google.com/rss/search?q=pipeline+incident+fire+explosion&hl=en&gl=US&ceid=US:en",
    },
    {
        "name": "Google News: refinery cyber security",
        "url": "https://news.google.com/rss/search?q=refinery+cyber+security&hl=en&gl=US&ceid=US:en",
    },
    {
        "name": "BleepingComputer",
        "url": "https://www.bleepingcomputer.com/feed/",
    },
    {
        "name": "DarkReading",
        "url": "https://www.darkreading.com/rss_simple.xml",
    },
    {
        "name": "Rigzone (energy incidents)",
        "url": "https://www.rigzone.com/news/rss/rigzone_latest.aspx",
    },
]


KEYWORDS = {
    "Физический доступ": [
        "break-in",
        "intrusion",
        "physical",
        "sabotage",
        "theft",
        "fire",
        "explosion",
        "blast",
        "pipeline",
        "refinery",
        "terminal",
        "shutdown",
    ],
    "Кибератаки ICS/SCADA": [
        "ransomware",
        "malware",
        "apt",
        "ics",
        "scada",
        "plc",
        "controller",
        "vpn",
        "industrial",
        "critical infrastructure",
        "cyber",
        "hack",
        "breach",
        "attack",
    ],
    "Финансы и мошенничество": [
        "fraud",
        "finance",
        "payment",
        "billing",
        "extortion",
        "blackmail",
        "stock",
        "market",
    ],
    "Персонал и инсайдеры": [
        "insider",
        "employee",
        "contractor",
        "social engineering",
        "phishing",
        "leaked",
        "whistleblower",
    ],
    "Экология и безопасность": [
        "spill",
        "leak",
        "emission",
        "environment",
        "safety",
        "regulator",
    ],
}


SSL_CONTEXT = ssl._create_unverified_context()


def parsed_date(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def first_text(elem: Optional[ET.Element]) -> str:
    return html.unescape(elem.text or "").strip() if elem is not None else ""


def classify(text: str) -> List[str]:
    low = text.lower()
    tags = []
    for label, words in KEYWORDS.items():
        if any(w in low for w in words):
            tags.append(label)
    return tags or ["Общее"]


def fetch_feed(source: Dict[str, str]) -> List[Dict[str, str]]:
    try:
        with urllib.request.urlopen(source["url"], context=SSL_CONTEXT, timeout=10) as resp:
            raw = resp.read()
    except urllib.error.URLError as exc:
        print(f"[warn] {source['name']}: {exc}", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        print(f"[warn] {source['name']}: XML parse failed {exc}", file=sys.stderr)
        return []

    items = []
    for item in root.findall(".//item"):
        title = first_text(item.find("title"))
        link = first_text(item.find("link"))
        desc = first_text(item.find("description"))
        pub = parsed_date(first_text(item.find("pubDate")))
        category = classify(f"{title} {desc}")
        if not title or not link:
            continue
        items.append(
            {
                "title": title,
                "link": link,
                "source": source["name"],
                "published": pub,
                "summary": desc,
                "categories": category,
            }
        )
    return items


def dedupe(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    unique = []
    for item in items:
        key = item["link"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def run() -> None:
    all_items: List[Dict[str, str]] = []
    summary = []
    for feed in FEEDS:
        entries = fetch_feed(feed)
        summary.append({"name": feed["name"], "url": feed["url"], "count": len(entries)})
        all_items.extend(entries)

    cleaned = dedupe(all_items)
    cleaned.sort(key=lambda x: x.get("published") or "", reverse=True)

    payload = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "sources": summary,
        "items": cleaned,
    }

    out_path = "data/news.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Collected {len(cleaned)} items from {len(FEEDS)} feeds -> {out_path}")


if __name__ == "__main__":
    run()

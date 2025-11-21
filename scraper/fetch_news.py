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
from pathlib import Path
from typing import Dict, List, Optional


FEEDS: List[Dict[str, str]] = [
    {
        "name": "Google Новости: нефтегаз кибератаки",
        "url": "https://news.google.com/rss/search?q=%D0%BD%D0%B5%D1%84%D1%82%D0%B5%D0%B3%D0%B0%D0%B7+%D0%BA%D0%B8%D0%B1%D0%B5%D1%80%D0%B0%D1%82%D0%B0%D0%BA%D0%B0&hl=ru&gl=RU&ceid=RU:ru",
    },
    {
        "name": "Google Новости: газопровод авария взрыв",
        "url": "https://news.google.com/rss/search?q=%D0%B3%D0%B0%D0%B7%D0%BE%D0%BF%D1%80%D0%BE%D0%B2%D0%BE%D0%B4+%D0%B0%D0%B2%D0%B0%D1%80%D0%B8%D1%8F+%D0%B2%D0%B7%D1%80%D1%8B%D0%B2&hl=ru&gl=RU&ceid=RU:ru",
    },
    {
        "name": "Google Новости: НПЗ кибербезопасность",
        "url": "https://news.google.com/rss/search?q=%D0%9D%D0%9F%D0%97+%D0%BA%D0%B8%D0%B1%D0%B5%D1%80%D0%B1%D0%B5%D0%B7%D0%BE%D0%BF%D0%B0%D1%81%D0%BD%D0%BE%D1%81%D1%82%D1%8C&hl=ru&gl=RU&ceid=RU:ru",
    },
    {
        "name": "SecurityLab (кибербезопасность)",
        "url": "https://www.securitylab.ru/_services/export/rss/",
    },
    {
        "name": "OilCapital (нефтегаз)",
        "url": "https://oilcapital.ru/rss",
    },
    {
        "name": "ComNews (телеком/промышленность)",
        "url": "https://www.comnews.ru/rss",
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
        "проникновение",
        "несанкционирован",
        "пожар",
        "взрыв",
        "газопровод",
        "трубопровод",
        "утечка газа",
        "перекрыли",
        "эвакуац",
        "физический доступ",
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
        "кибератака",
        "вирус",
        "вредонос",
        "vpn",
        "scada",
        "ics",
        "асу тп",
        "отр",
        "диспетчерск",
        "взлом",
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
        "мошеннич",
        "финанс",
        "расчёт",
        "платеж",
        "перевод",
        "рынок",
        "биржа",
        "вымогатель",
    ],
    "Персонал и инсайдеры": [
        "insider",
        "employee",
        "contractor",
        "social engineering",
        "phishing",
        "leaked",
        "whistleblower",
        "инсайдер",
        "сотрудник",
        "подрядчик",
        "фишинг",
        "утечка",
        "персонал",
        "кадр",
    ],
    "Экология и безопасность": [
        "spill",
        "leak",
        "emission",
        "environment",
        "safety",
        "regulator",
        "разлив",
        "утечка",
        "загрязн",
        "эколог",
        "безопасн",
        "пожарная",
        "сдт",
        "росприрод",
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

    root = Path(__file__).resolve().parents[1]
    out_paths = [root / "data/news.json", root / "public/data/news.json"]
    for out_path in out_paths:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    out_list = ", ".join(str(p) for p in out_paths)
    print(f"Collected {len(cleaned)} items from {len(FEEDS)} feeds -> {out_list}")


if __name__ == "__main__":
    run()

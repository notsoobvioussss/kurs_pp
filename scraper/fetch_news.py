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
        "name": "Google Новости: нефтегаз инцидент",
        "url": "https://news.google.com/rss/search?q=%D0%BD%D0%B5%D1%84%D1%82%D0%B5%D0%B3%D0%B0%D0%B7+%D0%B8%D0%BD%D1%86%D0%B8%D0%B4%D0%B5%D0%BD%D1%82&hl=ru&gl=RU&ceid=RU:ru",
    },
    {
        "name": "Google Новости: НПЗ авария пожар",
        "url": "https://news.google.com/rss/search?q=%D0%9D%D0%9F%D0%97+%D0%B0%D0%B2%D0%B0%D1%80%D0%B8%D1%8F+%D0%BF%D0%BE%D0%B6%D0%B0%D1%80&hl=ru&gl=RU&ceid=RU:ru",
    },
    {
        "name": "Google Новости: газопровод авария взрыв",
        "url": "https://news.google.com/rss/search?q=%D0%B3%D0%B0%D0%B7%D0%BE%D0%BF%D1%80%D0%BE%D0%B2%D0%BE%D0%B4+%D0%B0%D0%B2%D0%B0%D1%80%D0%B8%D1%8F+%D0%B2%D0%B7%D1%80%D1%8B%D0%B2&hl=ru&gl=RU&ceid=RU:ru",
    },
    {
        "name": "Google Новости: нефтегаз кибератака",
        "url": "https://news.google.com/rss/search?q=%D0%BD%D0%B5%D1%84%D1%82%D0%B5%D0%B3%D0%B0%D0%B7+%D0%BA%D0%B8%D0%B1%D0%B5%D1%80%D0%B0%D1%82%D0%B0%D0%BA%D0%B0&hl=ru&gl=RU&ceid=RU:ru",
    },
    {
        "name": "Google Новости: нефтебаза утечка разлив",
        "url": "https://news.google.com/rss/search?q=%D0%BD%D0%B5%D1%84%D1%82%D0%B5%D0%B1%D0%B0%D0%B7%D0%B0+%D1%83%D1%82%D0%B5%D1%87%D0%BA%D0%B0+%D1%80%D0%B0%D0%B7%D0%BB%D0%B8%D0%B2&hl=ru&gl=RU&ceid=RU:ru",
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
    {
        "name": "РБК (общая лента)",
        "url": "https://rssexport.rbc.ru/rbcnews/news/",
    },
]


KEYWORDS = {
    "Терроризм": [
        "теракт",
        "террор",
        "диверс",
        "взрывное устройство",
        "радикал",
        "боевик",
        "заложник",
        "экстремист",
        "саботаж",
        "заложников",
    ],
    "Физическая": [
        "проникновен",
        "несанкционирован",
        "скуд",
        "охран",
        "кража оборуд",
        "серверн",
        "пломб",
        "кабельн",
        "видеонаблюд",
        "physical",
        "intrusion",
        "цод",
        "стойк",
        "обход охраны",
    ],
    "Экология": [
        "эколог",
        "разлив",
        "загрязн",
        "выброс",
        "пдк",
        "сток",
        "сероводород",
        "утечка неф",
        "эмисси",
        "шлам",
    ],
    "Энергетика": [
        "подстанц",
        "энергос",
        "энергоснаб",
        "электроснаб",
        "рза",
        "ибп",
        "дгу",
        "блэкаут",
        "фидер",
        "энергобаланс",
        "распределит",
        "генерац",
        "грщ",
    ],
    "Инфобез": [
        "кибератак",
        "хак",
        "взлом",
        "ddos",
        "вредонос",
        "ransom",
        "malware",
        "apt",
        "фишинг",
        "утечк",
        "компрометац",
        "scada",
        "ics",
        "асу тп",
        "vpn",
        "учетные записи",
    ],
    "Психология": [
        "выгорание",
        "усталость",
        "давление",
        "шантаж",
        "мотивац",
        "забастов",
        "лояльн",
        "эмоциональ",
        "вербовк",
        "дезинформац",
    ],
    "Техногенная": [
        "авария",
        "техноген",
        "разгермет",
        "отказ оборуд",
        "сбой оборуд",
        "гидрат",
        "корроз",
        "турбин",
        "авария нпз",
        "авария скважин",
        "разрушение",
    ],
    "Пожарная": [
        "пожар",
        "возгора",
        "огне",
        "искра",
        "статическ",
        "апс",
        "аупт",
        "дым",
        "эвакуац",
        "огневые работы",
    ],
    "Экономическая": [
        "финанс",
        "эконом",
        "бирж",
        "рынок",
        "платеж",
        "кредит",
        "мошен",
        "вымогатель",
        "контрагент",
        "транзак",
        "логист",
        "поставк",
        "закуп",
        "отчетност",
    ],
    "Интеллектуальная": [
        "патент",
        "ноу-хау",
        "r&d",
        "геодан",
        "рецептур",
        "проектн",
        "чертеж",
        "инженерн",
        "секретн",
        "seismic",
        "petrel",
        "геологическ",
    ],
}

OIL_GAS_TERMS = [
    "нефтегаз",
    "нефть",
    "газ",
    "lng",
    "спг",
    "буров",
    "скважин",
    "газопровод",
    "трубопровод",
    "нефтепровод",
    "нпз",
    "нефтепереработ",
    "нефтехим",
    "месторожден",
    "платформа",
    "refinery",
    "pipeline",
    "oil",
    "petro",
    "petroleum",
]


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
    return tags or ["Инфобез"]


def is_oil_gas(text: str) -> bool:
    low = text.lower()
    return any(term in low for term in OIL_GAS_TERMS)


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
        blob = f"{title} {desc}"
        if not is_oil_gas(blob):
            continue
        category = classify(blob)
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

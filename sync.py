#!/usr/bin/env python3
"""Legge il database "Library" di Notion e rigenera books.json per la libreria.

Uso:
  NOTION_TOKEN=secret_xxx python3 sync.py
Variabili opzionali: LIBRARY_DS_ID (data source del database Library).
Solo libreria standard: gira sia in locale sia su GitHub Actions.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

DS_ID = os.environ.get("LIBRARY_DS_ID", "b6efa415-dc82-4e35-a112-6590b91ff129")
NOTION_VERSION = "2025-09-03"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.json")


def http_json(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def notion_rows(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        res = http_json(
            f"https://api.notion.com/v1/data_sources/{DS_ID}/query",
            json.dumps(body).encode(),
            headers,
        )
        rows += res["results"]
        if not res.get("has_more"):
            return rows
        cursor = res["next_cursor"]


def text(prop):
    if not prop:
        return None
    t = prop["type"]
    if t in ("title", "rich_text"):
        return "".join(x["plain_text"] for x in prop[t]).strip() or None
    if t in ("select", "status"):
        return prop[t]["name"] if prop[t] else None
    if t == "multi_select":
        return [x["name"] for x in prop[t]]
    if t == "number":
        return prop[t]
    if t == "checkbox":
        return prop[t]
    if t == "date":
        return prop[t]["start"] if prop[t] else None
    return None


def to_book(page):
    p = page["properties"]
    cover = page.get("cover") or {}
    rating = text(p.get("Rating")) or ""
    return {
        "id": page["id"],
        "url": page["url"],
        "title": text(p.get("Name")) or "Senza titolo",
        "author": text(p.get("Author")),
        "publisher": text(p.get("Editore")),
        "genres": text(p.get("Genre")) or [],
        "rating": rating.count("★"),
        "status": text(p.get("Status")) or "Not started",
        "pages": text(p.get("Total Pages")),
        "pagesRead": text(p.get("Pages Read")),
        "finished": text(p.get("Date Finished")),
        "overview": text(p.get("Overview")),
        # Solo le copertine "link" sono stabili: i file caricati scadono dopo un'ora.
        "cover": cover["external"]["url"] if cover.get("type") == "external" else None,
        "created": page["created_time"],
    }


def openlibrary_cover(book):
    q = {"title": book["title"], "limit": 5, "fields": "cover_i"}
    if book.get("author"):
        q["author"] = book["author"]
    try:
        res = http_json(
            "https://openlibrary.org/search.json?" + urllib.parse.urlencode(q),
            headers={"User-Agent": "libreria-notion (elisamagli)"},
        )
    except Exception as e:
        print(f"  copertina non trovata per {book['title']}: {e}", file=sys.stderr)
        return None
    for d in res.get("docs", []):
        if d.get("cover_i"):
            return f"https://covers.openlibrary.org/b/id/{d['cover_i']}-L.jpg"
    return None


def enrich_covers(books, previous):
    """Cerca su Open Library solo i libri nuovi, riusando le ricerche già fatte."""
    cache = {b["id"]: b for b in previous}
    for b in books:
        old = cache.get(b["id"])
        if b["cover"]:
            continue
        if old and old.get("title") == b["title"] and "autoCover" in old:
            b["autoCover"] = old["autoCover"]
        else:
            b["autoCover"] = openlibrary_cover(b)
    return books


def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        sys.exit("Manca NOTION_TOKEN")
    try:
        with open(OUT) as f:
            previous = json.load(f)["books"]
    except (OSError, ValueError, KeyError):
        previous = []
    books = [to_book(p) for p in notion_rows(token)]
    books.sort(key=lambda b: b["created"])
    enrich_covers(books, previous)
    with open(OUT, "w") as f:
        json.dump({"books": books}, f, ensure_ascii=False, indent=1)
    print(f"{len(books)} libri scritti in books.json")


if __name__ == "__main__":
    main()

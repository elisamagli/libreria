#!/usr/bin/env python3
"""Legge il database "Library" di Notion e rigenera books.json per la libreria.

Uso:
  NOTION_TOKEN=secret_xxx python3 sync.py
Variabili opzionali: LIBRARY_DS_ID (data source del database Library).
Solo libreria standard: gira sia in locale sia su GitHub Actions.

Copertina di un libro: la prima immagine dentro la sua pagina Notion
(in mancanza, la copertina della pagina). I file caricati su Notion hanno
link che scadono dopo un'ora, quindi vengono scaricati in covers/.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

DS_ID = os.environ.get("LIBRARY_DS_ID", "b6efa415-dc82-4e35-a112-6590b91ff129")
NOTION_VERSION = "2025-09-03"
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "books.json")
COVERS = os.path.join(ROOT, "covers")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def http_json(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def notion_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def notion_rows(token):
    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        res = http_json(
            f"https://api.notion.com/v1/data_sources/{DS_ID}/query",
            json.dumps(body).encode(),
            notion_headers(token),
        )
        rows += res["results"]
        if not res.get("has_more"):
            return rows
        cursor = res["next_cursor"]


def file_url(obj):
    """URL di un oggetto file Notion (caricato o link esterno)."""
    if not obj:
        return None
    if obj.get("type") == "file":
        return obj["file"]["url"]
    if obj.get("type") == "external":
        return obj["external"]["url"]
    return None


def cover_source(token, page):
    """(chiave stabile, url) della copertina, o (None, None)."""
    res = http_json(
        f"https://api.notion.com/v1/blocks/{page['id']}/children?page_size=25",
        headers=notion_headers(token),
    )
    for block in res["results"]:
        if block["type"] == "image":
            url = file_url(block["image"])
            if url:
                # L'id del blocco cambia solo se l'immagine viene sostituita
                key = block["id"] + ":" + (block.get("last_edited_time") or "")
                return key, url
    url = file_url(page.get("cover"))
    if url:
        return "cover:" + url.split("?")[0], url
    return None, None


def download_cover(page_id, url):
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
    if ext not in IMAGE_EXT:
        ext = ".jpg"
    name = page_id.replace("-", "") + ext
    os.makedirs(COVERS, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "libreria-notion"})
    with urllib.request.urlopen(req, timeout=60) as r, open(os.path.join(COVERS, name), "wb") as f:
        f.write(r.read())
    return "covers/" + name


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
        "cover": None,
        "coverKey": None,
        "created": page["created_time"],
    }


def attach_covers(token, pages, books, previous):
    """Scarica solo le copertine nuove o cambiate e rimuove quelle orfane."""
    cache = {b["id"]: b for b in previous}
    for page, b in zip(pages, books):
        try:
            key, url = cover_source(token, page)
        except Exception as e:
            print(f"  blocchi non leggibili per {b['title']}: {e}", file=sys.stderr)
            key, url = None, None
        old = cache.get(b["id"], {})
        if key and key == old.get("coverKey") and old.get("cover") and os.path.exists(os.path.join(ROOT, old["cover"])):
            b["cover"], b["coverKey"] = old["cover"], key
        elif key:
            try:
                b["cover"], b["coverKey"] = download_cover(b["id"], url), key
                print(f"  copertina aggiornata: {b['title']}")
            except Exception as e:
                print(f"  copertina non scaricata per {b['title']}: {e}", file=sys.stderr)
    used = {os.path.basename(b["cover"]) for b in books if b["cover"]}
    if os.path.isdir(COVERS):
        for name in os.listdir(COVERS):
            if name not in used:
                os.remove(os.path.join(COVERS, name))


def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        sys.exit("Manca NOTION_TOKEN")
    try:
        with open(OUT) as f:
            previous = json.load(f)["books"]
    except (OSError, ValueError, KeyError):
        previous = []
    pages = sorted(notion_rows(token), key=lambda p: p["created_time"])
    books = [to_book(p) for p in pages]
    attach_covers(token, pages, books, previous)
    with open(OUT, "w") as f:
        json.dump({"books": books}, f, ensure_ascii=False, indent=1)
    print(f"{len(books)} libri scritti in books.json")


if __name__ == "__main__":
    main()

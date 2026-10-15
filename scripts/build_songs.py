#!/usr/bin/env python3
"""Build the "Released" song list on linkkehub.html from data/songs/*.json.

Agents add a song by committing ONE small JSON file to data/songs/ (and,
optionally, a cover image to assets/covers/src/). They never edit HTML. This
script validates every entry, makes the cover thumbnails, and rewrites only the
part of linkkehub.html between the songs:start / songs:end markers.

The gate: an entry must point at The executive's own post on X (x_post). The
executive posting a song is his approval (The executive, 2026-10-13 10:02 MT),
so nothing reaches this page that he hasn't already released himself.

Run:  python3 scripts/build_songs.py           (validate + render)
      python3 scripts/build_songs.py --check   (validate only, change nothing)
Pause: create data/PAUSE and the page is left as it is.
Unpublish: set "hidden": true in the song's file, or delete the file.

Standard library only, plus Pillow for cover thumbnails.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SONGS = os.path.join(ROOT, "data", "songs")
PAGE = os.path.join(ROOT, "linkkehub.html")
COVERS = os.path.join(ROOT, "assets", "covers")
SRC = os.path.join(COVERS, "src")
PAUSE = os.path.join(ROOT, "data", "PAUSE")
START, END = "<!-- songs:start -->", "<!-- songs:end -->"

FIELDS = {"id", "title", "subtitle", "released", "x_post", "suno_url", "cover", "cover_alt", "hidden"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,58}[a-z0-9]$")
X_RE = re.compile(r"^https://x\.com/humanvsmachineX/status/(\d{15,20})$")
SUNO_RE = re.compile(r"^https://suno\.com/(song/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|s/[A-Za-z0-9]{6,32})$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COVER_RE = re.compile(r"^assets/(covers/src/[a-z0-9-]+\.(png|jpg|jpeg|webp)|(covers/)?[a-z0-9-]+-400\.webp)$")
LIMITS = {"title": 80, "subtitle": 60, "cover_alt": 600}


def check(path):
    """Return (entry, errors) for one song file."""
    name = os.path.basename(path)
    try:
        with open(path, encoding="utf-8") as f:
            e = json.load(f)
    except (OSError, ValueError) as ex:
        return None, [f"{name}: not valid JSON ({ex})"]
    errs = []
    if not isinstance(e, dict):
        return None, [f"{name}: must be a JSON object"]
    extra = set(e) - FIELDS
    if extra:
        errs.append(f"{name}: unknown field(s) {sorted(extra)}")
    for k in ("id", "title", "released", "x_post"):
        if not isinstance(e.get(k), str) or not e[k].strip():
            errs.append(f"{name}: '{k}' is required")
    if errs:
        return e, errs
    if not ID_RE.match(e["id"]) or name != e["id"] + ".json":
        errs.append(f"{name}: id must be lowercase-with-dashes and match the file name")
    if not DATE_RE.match(e["released"]):
        errs.append(f"{name}: released must be YYYY-MM-DD")
    if not X_RE.match(e["x_post"]):
        errs.append(f"{name}: x_post must be a post on @humanvsmachineX (https://x.com/humanvsmachineX/status/<id>)")
    if e.get("suno_url") is not None and not (isinstance(e["suno_url"], str) and SUNO_RE.match(e["suno_url"])):
        errs.append(f"{name}: suno_url must be https://suno.com/song/<uuid> or https://suno.com/s/<code>, no ?query")
    for k, n in LIMITS.items():
        v = e.get(k)
        if v is None:
            continue
        if not isinstance(v, str):
            errs.append(f"{name}: {k} must be text")
        elif len(v) > n:
            errs.append(f"{name}: {k} is longer than {n} characters")
        elif re.search(r"[<>]|https?://", v):
            errs.append(f"{name}: {k} may not contain < > or links")
    if e.get("hidden") not in (None, True, False):
        errs.append(f"{name}: hidden must be true or false")
    if e.get("cover") is not None:
        c = e["cover"]
        if not (isinstance(c, str) and COVER_RE.match(c)):
            errs.append(f"{name}: cover must be assets/covers/src/<name>.png|jpg|webp or a ready 400px assets/[covers/]<name>-400.webp")
        elif not os.path.isfile(os.path.join(ROOT, c)):
            errs.append(f"{name}: cover file {c} is not in the repo")
        elif os.path.getsize(os.path.join(ROOT, c)) > 8 * 1024 * 1024:
            errs.append(f"{name}: cover file is over 8 MB")
        if not e.get("cover_alt"):
            errs.append(f"{name}: cover_alt (a description of the image for screen readers) is required with a cover")
    return e, errs


def thumb(e):
    """Path (relative to the page) of the 400px cover thumbnail, making it if needed."""
    c = e.get("cover")
    if not c:
        return None
    if c.endswith("-400.webp"):
        return c
    out_rel = f"assets/covers/{e['id']}-400.webp"
    out = os.path.join(ROOT, out_rel)
    src = os.path.join(ROOT, c)
    if not os.path.isfile(out) or os.path.getmtime(out) < os.path.getmtime(src):
        from PIL import Image
        with Image.open(src) as im:
            im = im.convert("RGB")
            w, h = im.size
            s = min(w, h)
            im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((400, 400), Image.LANCZOS)
            im.save(out, "WEBP", quality=82, method=6)
    return out_rel


def render(entries):
    lines = []
    for e in entries:
        t = html.escape
        href = e.get("suno_url") or e["x_post"]
        where = "Play on Suno" if e.get("suno_url") else "Watch on X"
        img = ""
        th = thumb(e)
        if th:
            img = (f'<img class="thumb" src="{t(th)}" width="400" height="400" loading="lazy" decoding="async" '
                   f'alt="{t(e["cover_alt"])}">')
        sub = f'<small>{t(e["subtitle"])}</small>' if e.get("subtitle") else ""
        lines.append(f'        <li><a href="{t(href)}" target="_blank" rel="noopener">{img}<span class="big">{t(e["title"])}{sub}</span>'
                     f'<span class="label">{where} ↗</span><span class="sr"> (opens in a new tab)</span></a></li>')
    return "\n".join(lines)


def main():
    only_check = "--check" in sys.argv
    files = sorted(os.path.join(SONGS, n) for n in os.listdir(SONGS) if n.endswith(".json")) if os.path.isdir(SONGS) else []
    with open(PAGE, encoding="utf-8") as f:
        page = f.read()
    a, b = page.find(START), page.find(END)
    if a < 0 or b < a:
        print("::error::songs markers missing from linkkehub.html")
        sys.exit(2)
    live = page[a:b]
    valid, bad = [], []
    for p in files:
        e, errs = check(p)
        if errs:
            bad += errs
        else:
            valid.append((os.path.basename(p), e))
    # Two files claiming the same X post: keep the one already on the page, so a
    # new file can never knock a released song off. If neither is live, show neither.
    by_post = {}
    for name, e in valid:
        by_post.setdefault(X_RE.match(e["x_post"]).group(1), []).append((name, e))
    good = []
    for group in by_post.values():
        if len(group) > 1:
            names = ", ".join(n for n, _ in group)
            on_page = [(n, e) for n, e in group if html.escape(e.get("suno_url") or e["x_post"]) in live]
            keep = on_page[0] if len(on_page) == 1 else None
            for n, e in group:
                if keep is None or n != keep[0]:
                    bad.append(f"{n}: same x_post as another file ({names}); not shown")
            group = [keep] if keep else []
        good += [e for _, e in group if not e.get("hidden")]
    for msg in bad:
        print(f"::error::{msg}")
    # Newest first. X post ids are time-ordered, so they break ties within a day.
    good.sort(key=lambda e: (e["released"], int(X_RE.match(e["x_post"]).group(1))), reverse=True)
    print(f"{len(good)} song(s) to show, {len(bad)} problem(s)")
    if only_check:
        sys.exit(1 if bad else 0)
    if os.path.exists(PAUSE):
        print("data/PAUSE exists: page left unchanged")
        sys.exit(1 if bad else 0)
    a_end = a + len(START)
    new = page[:a_end] + "\n" + render(good) + "\n        " + page[b:]
    if new != page:
        with open(PAGE, "w", encoding="utf-8") as f:
            f.write(new)
        print("linkkehub.html updated")
    else:
        print("linkkehub.html already up to date")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

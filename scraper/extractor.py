from bs4 import BeautifulSoup, Tag
from typing import Optional

_STRIP_TAGS = [
    "script", "style", "noscript", "iframe", "link", "meta",
    "svg", "canvas", "template",
]

_STRIP_SEMANTIC = ["header", "footer", "nav", "aside"]

# Partial strings matched against class/id values (lowercase)
_BOILERPLATE_KEYWORDS = [
    "navbar", "navigation", "menu", "topbar", "header", "footer",
    "sidebar", "cookie", "banner", "popup", "modal", "overlay",
    "sticky", "breadcrumb", "pagination", "social", "newsletter",
    "cta-banner", "advertisement", "widget", "related", "share",
    "back-to-top", "scroll-top", "chat-widget", "intercom",
]


def _is_boilerplate(el: Tag) -> bool:
    classes = " ".join(el.get("class") or []).lower()
    el_id = (el.get("id") or "").lower()
    combined = f"{classes} {el_id}"
    return any(kw in combined for kw in _BOILERPLATE_KEYWORDS)


def extract_content(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    # --- Title ---
    title = ""
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    elif soup.title:
        raw = soup.title.get_text(strip=True)
        # "Page Title | Radix Web" → "Page Title"
        for sep in (" | ", " - ", " – ", " — "):
            if sep in raw:
                raw = raw.split(sep)[0].strip()
                break
        title = raw

    # --- Meta description ---
    description = ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc["content"].strip()

    # Remove technical tags first
    for tag_name in _STRIP_TAGS:
        for el in soup.find_all(tag_name):
            el.decompose()

    # Remove structural boilerplate tags
    for tag_name in _STRIP_SEMANTIC:
        for el in soup.find_all(tag_name):
            el.decompose()

    # Remove elements whose class/id hint they're boilerplate
    for el in soup.find_all(True):
        try:
            if _is_boilerplate(el):
                el.decompose()
        except Exception:
            pass

    # --- Find main content area ---
    main: Optional[Tag] = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id=lambda x: x and "main" in x.lower())
        or soup.find(id="content")
        or soup.find(class_=lambda x: x and "main-content" in " ".join(x).lower() if x else False)
        or soup.body
    )

    if not main:
        return {"title": title, "description": description, "html": "", "url": url}

    return {
        "title": title,
        "description": description,
        "html": str(main),
        "url": url,
    }

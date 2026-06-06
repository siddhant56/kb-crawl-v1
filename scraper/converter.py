import re
import html2text

_h = html2text.HTML2Text()
_h.ignore_links = True       # keep text, drop raw URLs cluttering the output
_h.ignore_images = True      # images are irrelevant for RAG text
_h.ignore_emphasis = False
_h.body_width = 0            # no hard line-wrapping
_h.unicode_snob = True
_h.skip_internal_links = True
_h.single_line_break = False


def _clean_markdown(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)          # collapse excess blank lines
    text = re.sub(r"[ \t]+\n", "\n", text)           # trailing whitespace
    text = re.sub(r"\n+(\s*[*\-]{3,}\s*)\n+", "\n\n---\n\n", text)  # tidy HR
    return text.strip()


def to_markdown(extracted: dict) -> str:
    title = extracted.get("title", "")
    description = extracted.get("description", "")
    url = extracted.get("url", "")
    html_content = extracted.get("html", "")

    md_body = _h.handle(html_content) if html_content else ""
    md_body = _clean_markdown(md_body)

    # Skip pages that produced essentially no content
    if len(md_body) < 100:
        return ""

    parts: list[str] = []
    if title:
        parts.append(f"# {title}")
    if description:
        parts.append(f"\n> {description}")
    parts.append(f"\n**Source:** {url}\n")
    parts.append("---\n")
    parts.append(md_body)

    return "\n".join(parts)

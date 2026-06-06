import re
import hashlib
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urljoin, parse_qs, urlencode

RADIXWEB_HOST = "radixweb.com"   # apex domain — www. has no DNS
RADIXWEB_BASE = "https://radixweb.com"

# ---------------------------------------------------------------------------
# Category rules — ordered, first match wins.
# Derived from the actual sitemap (1 964 URLs across 30+ path prefixes).
# ---------------------------------------------------------------------------
CATEGORY_RULES: list[tuple[str, str]] = [
    # ── Blog / Editorial — FIRST so /company-news/* beats generic rules ───
    (r"^/blog(/|$|-)", "blog"),
    (r"^/company-news(/|$|-)", "blog"),
    (r"^/insights?(/|$|-)", "blog"),
    (r"^/webstories?(/|$|-)", "blog"),

    # ── Hire Developers — before generic -development suffix rule ──────────
    (r"^/hire-", "hire-developers"),
    (r".+-developers?(/|$)", "hire-developers"),
    (r".+-engineers?(/|$)", "hire-developers"),

    # ── Case Studies / Portfolio ───────────────────────────────────────────
    (r"^/case-studies?(/|$|-)", "case-studies"),
    (r"^/success-stories?(/|$|-)", "case-studies"),
    (r"^/tech-studies?(/|$|-)", "case-studies"),

    # ── Industries ─────────────────────────────────────────────────────────
    (r"^/industries?(/|$|-)", "industries"),
    (r"^/software-and-hi-tech(/|$)", "industries"),

    # ── Resources — BEFORE generic -development suffix rule ───────────────
    (r"^/guides?(/|$|-)", "resources"),
    (r"^/whitepapers?(/|$|-)", "resources"),
    (r"^/resources?(/|$|-)", "resources"),
    (r"^/reports?(/|$|-)", "resources"),
    (r"^/frameworks?(/|$|-)", "resources"),
    (r"^/podcast(/|$|-)", "resources"),
    (r"^/starter-kits?(/|$|-)", "resources"),
    (r"^/videos?(/|$|-)", "resources"),
    (r"^/(global-|ai-failure-report|ai-in-)", "resources"),

    # ── About (culture, leadership, values, identity) ─────────────────────
    (r"^/about", "about"),
    (r"^/our-", "about"),
    (r"^/leadership(/|$)", "about"),
    (r"^/diversity-", "about"),
    (r"^/women-at-", "about"),
    (r"^/(great-place-to-work|radixweb-as-a-workplace)(/|$)", "about"),
    (r"^/value-proposition(/|$)", "about"),
    (r"^/why-us(/|$)", "about"),
    (r"^/partners?(/|$)", "about"),
    (r"^/testimonials(/|$)", "about"),
    (r"^/innovation-", "about"),
    (r"^/talent-development", "about"),
    (r"^/software-development-methodologies(/|$)", "about"),
    (r"^/software-outsourcing-business-models(/|$)", "about"),
    (r"^/project-management-methodologies(/|$)", "about"),
    (r"^/collaboration(/|$)", "about"),
    (r"^/high-performance-teams(/|$)", "about"),
    (r"^/technology-expertise(/|$)", "about"),
    (r"^/author(/|$|-)", "about"),

    # ── Company (contact, careers, events, location pages) ────────────────
    (r"^/contact", "company"),
    (r"^/careers?(/|$)", "company"),
    (r"^/current-openings(/|$)", "company"),
    (r"^/events?(/|$|-)", "company"),
    (r"^/areas-we-serve(/|$)", "company"),
    (r"^/radixweb-anniversary(/|$)", "company"),
    (r"^/new-office-", "company"),
    (r"^/data-security-", "company"),
    (r"^/security-management(/|$)", "company"),
    (r"^/quality-management(/|$)", "company"),
    (r"^/software-development-company-", "company"),
    (r"^/mobile-app-development-company-", "company"),
    (r"^/web-development-company-", "company"),

    # ── Services — LAST so generic suffix rules don't steal from above ─────
    (r"^/services(/|$|-)", "services"),
    (r"^/solutions(/|$|-)", "services"),
    (r"^/salesforce(/|$|-)", "services"),
    (r"^/servicenow(/|$|-)", "services"),
    (r"^/application-migration(/|$)", "services"),
    (r"^/application-modernization(/|$)", "services"),
    (r"^/database-management(/|$)", "services"),
    (r"^/low-code(/|$)", "services"),
    (r"^/power-bi-consulting(/|$)", "services"),
    (r"^/zoho-crm-consulting(/|$)", "services"),
    (r"^/aws-devops(/|$)", "services"),
    # Named-technology service pages: /reactjs-development, /nodejs-development …
    (r"^/(reactjs|vuejs|angular|nodejs|python|django|flask|laravel|php|"
     r"ruby-on-rails|ionic|xamarin|flutter|swift|kotlin|java|typescript|"
     r"dotnet|net|mean-stack|mern-stack|meteorjs|nestjs|expressjs|fastify|"
     r"aws|azure|google-app-engine|mongodb|postgresql|mysql|firebase|"
     r"dynamodb|sqlite|sql-server|magento|shopify|woocommerce|wordpress|"
     r"joomla|strapi|jamstack|tezjs|codeigniter|cakephp|react-native|"
     r"introduction-to|what-is|what-are|on-demand)(/|-|$)", "services"),
    # Catch-all: any root-level page whose path ends with -development
    (r"^/[^/]+-development(/|$)", "services"),
    (r"^/full-stack-development(/|$)", "services"),
    (r"^/front-end-development(/|$)", "services"),
    (r"^/backend-development(/|$)", "services"),
    (r"^/no-code-development(/|$)", "services"),
    (r"^/headless-cms-development(/|$)", "services"),
]

_TRACKING_PARAMS = frozenset(
    {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
     "fbclid", "gclid", "_ga", "ref"}
)

_SKIP_EXTENSIONS = frozenset(
    {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".css", ".js",
     ".zip", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
     ".mp4", ".mp3", ".webm", ".webp", ".woff", ".woff2", ".ttf", ".eot"}
)

_SKIP_PATH_PATTERNS = [
    r"/wp-admin/", r"/wp-login", r"/feed/?$",
    r"\.xml(\?|$)", r"\.json(\?|$)",
    r"/sitemap", r"/xmlrpc\.php",
    r"^/start/",          # disallowed in robots.txt
    r"^/privacy-policy(/|$)",   # legal boilerplate — low RAG value
    r"^/terms-of-use(/|$)",
    r"^/no-gift-policy(/|$)",
]


def normalize_url(url: str, base: str = RADIXWEB_BASE) -> Optional[str]:
    try:
        full = urljoin(base, url)
        parsed = urlparse(full)
        if parsed.scheme not in ("http", "https"):
            return None
        host = parsed.netloc.lower()
        # Allow radixweb.com and www.radixweb.com (normalise to apex)
        if RADIXWEB_HOST not in host:
            return None
        params = parse_qs(parsed.query, keep_blank_values=True)
        clean_params = {k: v for k, v in params.items() if k not in _TRACKING_PARAMS}
        clean_query = urlencode(clean_params, doseq=True)
        normalized = parsed._replace(
            scheme="https",
            netloc=RADIXWEB_HOST,   # strip www. if present
            fragment="",
            query=clean_query,
        )
        return normalized.geturl()
    except Exception:
        return None


def should_skip(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    if Path(path).suffix.lower() in _SKIP_EXTENSIONS:
        return True
    for pattern in _SKIP_PATH_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return True
    return False


def categorize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.lower()

    if path in ("", "/", "/index.html"):
        return "company"

    for pattern, category in CATEGORY_RULES:
        if re.search(pattern, path):
            return category

    # Fallback: use the first path segment as the folder name
    segments = [s for s in path.split("/") if s]
    if segments:
        seg = re.sub(r"[^\w-]", "", segments[0])[:40]
        return seg or "general"

    return "general"


def url_to_filename(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        path = "index"

    safe = re.sub(r"[^\w\-]", "-", path.replace("/", "-"))
    safe = re.sub(r"-+", "-", safe).strip("-")[:180]

    if parsed.query:
        h = hashlib.md5(parsed.query.encode()).hexdigest()[:6]
        safe = f"{safe}-{h}"

    return (safe or "page") + ".md"

import threading
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScrapeState:
    status: str = "idle"  # idle | running | completed | failed
    pages_scraped: int = 0
    pages_discovered: int = 0
    pages_skipped: int = 0
    current_url: Optional[str] = None
    categories: dict = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def reset(self):
        self.status = "idle"
        self.pages_scraped = 0
        self.pages_discovered = 0
        self.pages_skipped = 0
        self.current_url = None
        self.categories = {}
        self.error = None
        self.started_at = None
        self.completed_at = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "pages_scraped": self.pages_scraped,
            "pages_discovered": self.pages_discovered,
            "pages_skipped": self.pages_skipped,
            "current_url": self.current_url,
            "categories": self.categories,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


scrape_state = ScrapeState()
scrape_lock = threading.Lock()

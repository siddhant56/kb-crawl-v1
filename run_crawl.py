import asyncio
import sys
from scraper import run_full_crawl

async def main():
    await run_full_crawl(max_pages=10000, workers=3)

asyncio.run(main())

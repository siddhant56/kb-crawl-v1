import asyncio
from scraper.extractor import extract_content
from scraper.converter import to_markdown

url = "https://radixweb.com/guides/security-factors-to-hire-developers"

async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # Scroll aggressively until no new content loads
        prev_height = 0
        for i in range(15):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            import asyncio as aio
            await aio.sleep(0.4)
            curr_height = await page.evaluate("document.body.scrollHeight")
            if curr_height == prev_height:
                break
            prev_height = curr_height

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        import asyncio as aio
        await aio.sleep(1.5)
        await page.evaluate("window.scrollTo(0, 0)")
        await aio.sleep(0.5)

        html = await page.content()
        await browser.close()

    print(f"Playwright HTML length: {len(html)}")

    extracted = extract_content(html, url)
    print(f"Extracted HTML length: {len(extracted['html'])}")

    md = to_markdown(extracted)
    print(f"Markdown length: {len(md)}")
    if not md:
        print(">>> SKIPPED")
    else:
        print(md)

asyncio.run(main())

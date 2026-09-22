from pathlib import Path
from playwright.sync_api import sync_playwright


PAGE = Path(__file__).resolve().parent / "demo_page.html"


def main():
    with sync_playwright() as p:

        chrome_path = Path("/Applications/Google Chrome.app")

        if chrome_path.exists():
            print("Browser backend: installed Google Chrome")

            browser = p.chromium.launch(
                channel="chrome",
                headless=False,
            )
        else:
            print("Browser backend: Playwright Chromium")

            browser = p.chromium.launch(
                headless=False,
            )

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 850,
            }
        )

        url = PAGE.as_uri()

        print()
        print("Opening:", url)

        page.goto(url)

        print("Page title:", page.title())

        print()
        print("Buttons detected:")

        buttons = page.get_by_role("button")

        for i in range(buttons.count()):
            button = buttons.nth(i)
            print(f"[{i}] {button.inner_text()}")

        print()
        print("Executing test action:")
        print("CLICK -> API Documentation")

        page.get_by_role(
            "button",
            name="API Documentation",
        ).click()

        result = page.locator("#result").inner_text()

        print()
        print("Browser returned:")
        print(result)

        if result == "API DOCUMENTATION FOUND":
            print()
            print("PLAYWRIGHT_SMOKE_TEST=PASS")
        else:
            print()
            print("PLAYWRIGHT_SMOKE_TEST=FAIL")

        print()
        print("Keeping browser visible briefly...")

        page.wait_for_timeout(5000)

        browser.close()


if __name__ == "__main__":
    main()

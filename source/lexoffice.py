import os
import requests
import urllib.parse
from time import sleep
import threading

# Try to import Playwright dependencies
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError as e:
    print(f"[Lexoffice] Warning: Playwright not available. AWS WAF bypass disabled. Error: {e}")

LEXOFFICE_BASE_URL = "https://app.lexware.de"
_session = None
_waf_cookies = None

BROWSER_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": "https://app.lexware.de",
    "referer": "https://app.lexware.de/sign-in/authenticate",
    "sec-ch-ua": '"Chromium";v="142", "Not A(Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
}

def _run_playwright_in_thread(username, password, result_container):
    """Helper function to run Playwright in a separate thread to avoid asyncio conflicts."""
    try:
        with sync_playwright() as p:
            # Launch browser with stealth settings
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )

            # Create context with realistic browser fingerprint
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='Europe/Berlin',
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            )

            # Add script to override navigator.webdriver
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            page = context.new_page()

            # Navigate to login page
            login_url = urllib.parse.urljoin(LEXOFFICE_BASE_URL, 'sign-in/authenticate')
            print(f"[Lexoffice] Navigating to {login_url}")

            page.goto(login_url, wait_until='domcontentloaded', timeout=30000)

            # Wait for page to load
            sleep(2)
            print(f"[Lexoffice] Current URL: {page.url}")
            print(f"[Lexoffice] Page title: {page.title()}")

            # Wait for AWS WAF challenge to complete
            print("[Lexoffice] Waiting for AWS WAF challenge to resolve...")
            sleep(5)

            print(f"[Lexoffice] After WAF wait - URL: {page.url}")
            print(f"[Lexoffice] Page title: {page.title()}")

            # Check if we got past WAF
            if '403' in page.title() or 'Forbidden' in page.title():
                print("[Lexoffice] Still blocked by WAF, trying longer wait...")
                sleep(10)
                page.reload(wait_until='domcontentloaded')
                sleep(5)

            # Handle cookie consent banner if present
            try:
                # Try to find and dismiss cookie consent
                print("[Lexoffice] Checking for cookie consent banner...")
                # Common cookie consent button selectors
                consent_selectors = [
                    'button:has-text("Accept")',
                    'button:has-text("Akzeptieren")',
                    'button:has-text("Alle akzeptieren")',
                    'button[data-testid="uc-accept-all-button"]',
                    '#usercentrics-root button',
                ]

                for selector in consent_selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            page.click(selector, timeout=2000)
                            print(f"[Lexoffice] Clicked cookie consent with selector: {selector}")
                            sleep(1)
                            break
                    except:
                        continue
            except Exception as e:
                print(f"[Lexoffice] No cookie consent banner found or error dismissing: {e}")

            # Try to find and fill login form
            print("[Lexoffice] Attempting login...")

            try:
                # Try different selectors for username field
                selectors = [
                    "input[type='email']",
                    "input[name='username']",
                    "input[name='email']"
                ]

                username_filled = False
                for selector in selectors:
                    try:
                        page.wait_for_selector(selector, timeout=5000)
                        page.fill(selector, username)
                        print(f"[Lexoffice] Username entered with selector: {selector}")
                        username_filled = True
                        break
                    except:
                        continue

                if not username_filled:
                    print(f"[Lexoffice] Could not find username field")
                    print(f"[Lexoffice] Page content length: {len(page.content())}")
                    # Save screenshot
                    page.screenshot(path='/tmp/lexoffice_debug.png')
                    print("[Lexoffice] Screenshot saved to /tmp/lexoffice_debug.png")
                    raise Exception("Username field not found")

                # Fill password
                page.fill("input[type='password']", password)
                print("[Lexoffice] Password entered")

                # Click submit button
                page.click("button[type='submit']")
                print("[Lexoffice] Login form submitted")

                # Wait for navigation
                page.wait_for_load_state('networkidle', timeout=15000)
                sleep(3)

                print(f"[Lexoffice] After login - URL: {page.url}")
                print(f"[Lexoffice] After login - Title: {page.title()}")

            except Exception as e:
                print(f"[Lexoffice] Login error: {str(e)}")
                print(f"[Lexoffice] Current URL: {page.url}")
                print(f"[Lexoffice] Current title: {page.title()}")

            # Extract cookies
            cookies = {}
            playwright_cookies = context.cookies()
            for cookie in playwright_cookies:
                cookies[cookie['name']] = cookie['value']

            print(f"[Lexoffice] Extracted {len(cookies)} cookies from browser session")
            if cookies:
                print(f"[Lexoffice] Cookie names: {list(cookies.keys())}")

            browser.close()

            result_container['cookies'] = cookies if cookies else None

    except Exception as e:
        print(f"[Lexoffice] Error in Playwright thread: {e}")
        import traceback
        traceback.print_exc()
        result_container['cookies'] = None

def solve_aws_waf_challenge(username, password):
    """
    Solves AWS WAF challenge using Playwright and extracts cookies.
    Returns a dict of cookies that can be used with requests.Session.
    """
    global _waf_cookies

    if not PLAYWRIGHT_AVAILABLE:
        print("[Lexoffice] Cannot solve AWS WAF challenge - Playwright not installed")
        print("[Lexoffice] Install with: pip install playwright && playwright install chromium")
        return None

    print("[Lexoffice] Solving AWS WAF challenge with Playwright...")

    # Run Playwright in a separate thread to avoid asyncio conflicts
    result_container = {}
    thread = threading.Thread(
        target=_run_playwright_in_thread,
        args=(username, password, result_container)
    )
    thread.start()
    thread.join(timeout=60)  # 60 second timeout

    if thread.is_alive():
        print("[Lexoffice] Playwright thread timed out after 60 seconds")
        return None

    cookies = result_container.get('cookies')
    if cookies:
        _waf_cookies = cookies

    return cookies

def get_session(username=None, password=None):
    global _session, _waf_cookies
    if _session is None:
        _session = requests.Session()
        if username and password:
            # Always use Playwright if available due to AWS WAF
            if PLAYWRIGHT_AVAILABLE:
                if _waf_cookies is None:
                    print("[Lexoffice] Using Playwright to bypass AWS WAF protection...")
                    _waf_cookies = solve_aws_waf_challenge(username, password)

                if _waf_cookies:
                    # Apply the cookies from browser session to requests session
                    for name, value in _waf_cookies.items():
                        _session.cookies.set(name, value)
                    print("[Lexoffice] Successfully applied WAF cookies to session")
                    return _session
                else:
                    print("[Lexoffice] Failed to solve AWS WAF challenge")
                    _session = None
                    return None

            # Fallback for systems without Playwright (will likely fail with AWS WAF)
            print("[Lexoffice] WARNING: Playwright not available, trying direct API login (may fail due to AWS WAF)")
            url = urllib.parse.urljoin(
                LEXOFFICE_BASE_URL,
                'janus/janus-rest/public/login/web/v100/authenticate'
            )
            payload = {"username": username, "password": password}
            response = _session.post(url, json=payload, headers=BROWSER_HEADERS)
            print("Received cookies: ", response.cookies.get_dict())

            if response.status_code == 401:
                print("[Lexoffice] Auth failed. This could be due to:")
                print("  1. AWS WAF blocking the request (install Playwright to bypass)")
                print("  2. Invalid credentials")
                print("[Lexoffice] Install dependencies: pip install playwright && playwright install chromium")
                _session = None
            elif response.status_code != 200 and response.status_code != 202:
                print(f"[Lexoffice] Error creating session cookie: {response.status_code}")
                print(f"[Lexoffice] Response: {response.text[:200]}")
                _session = None
    return _session

def upload_voucher(filepath, username=None, password=None):
    filename = os.path.basename(filepath)
    print(f"[Lexoffice] Received filename {filename} to upload")

    headers = {
        'accept': '*/*',
        'origin': LEXOFFICE_BASE_URL,
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'x-bookkeeping-voucher-client': 'Belegliste',
    }

    session = get_session(username, password)
    url = urllib.parse.urljoin(
        LEXOFFICE_BASE_URL,
        'capsa/capsa-rest/v2/vouchers'
    )

    def post_file(session):
        with open(filepath, 'rb') as f:
            files = [
                ('datasource', (None, 'USER_BROWSER')),
                ('documents', (filename, f, 'application/pdf')),
            ]
            sleep(0.5)
            return session.post(url, headers=headers, files=files)

    if not session:
        print("[Lexoffice] Failed to create session, cannot upload document")
        return None

    response = post_file(session)

    if response.status_code == 401 and username and password:
        print("[Lexoffice] Returned unauthorized, attempting to refresh session...")
        global _session, _waf_cookies
        _session = None
        _waf_cookies = None  # Clear WAF cookies to force re-authentication
        session = get_session(username, password)
        if session:
            response = post_file(session)
        else:
            print("[Lexoffice] Failed to refresh session")
            return None

    # Handle response
    if response.status_code == 200:
        try:
            lexoffice_document_uuid = response.json().get('id', None)
            print(f"[Lexoffice] Document uploaded successfully, has lexoffice UUID {lexoffice_document_uuid}")
            return lexoffice_document_uuid
        except Exception as e:
            print(f"[Lexoffice] Error parsing response JSON: {e}")
            print(f"[Lexoffice] Response text: {response.text[:200]}")
            return None
    else:
        print(f"[Lexoffice] Request failed with status code: {response.status_code}")
        print(f"[Lexoffice] Response text: {response.text[:200]}")
        return None

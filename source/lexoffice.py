import requests
from time import sleep
import os

_cached_cookie = {}

def create_cookie(username, password):
    global _cached_cookie
    url = 'https://app.lexware.de/janus/janus-rest/public/login/web/v100/authenticate'
    payload = {"username": username, "password": password}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        cookies = {}
        # Manche Antworten enthalten mehrere Cookies, daher Split auf Kommas und Semikolons
        cookie_headers = response.headers.getlist("Set-Cookie") if hasattr(response.headers, "getlist") else [response.headers.get("Set-Cookie")]
        for cookie_str in cookie_headers:
            if cookie_str:
                for part in cookie_str.split(";"):
                    if "=" in part:
                        key, value = part.strip().split("=", 1)
                        cookies[key] = value
        _cached_cookie = cookies
        return _cached_cookie
    print(f"Error creating cookie: {response.status_code}")
    return None

def upload_voucher(filepath, username=None, password=None):
    global _cached_cookie

    filename = os.path.basename(filepath)
    print(f"Got filename {filename} to upload")

    # Header wie im funktionierenden Postman-Request
    headers = {
        'accept': '*/*',
        'origin': 'https://app.lexware.de',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'x-bookkeeping-voucher-client': 'Belegliste',
    }

    with open(filepath, 'rb') as f:
        files = [
            ('datasource', (None, 'USER_BROWSER')),
            ('documents', (filename, f, 'application/pdf')),
        ]

        sleep(0.5)
        response = requests.post(
            'https://app.lexware.de/capsa/capsa-rest/v2/vouchers',
            headers=headers,
            files=files,
            cookies=_cached_cookie if _cached_cookie else None
        )

    # 401? Cookie neu erstellen
    if response.status_code == 401 and username and password:
        print("Unauthorized. Refreshing cookie...")
        new_cookie = create_cookie(username, password)
        if new_cookie:
            print("Cookie refreshed successfully, attempting upload again...")
            with open(filepath, 'rb') as f:
                files = [
                    ('datasource', (None, 'USER_BROWSER')),
                    ('documents', (filename, f, 'application/pdf')),
                ]
                response = requests.post(
                    'https://app.lexware.de/capsa/capsa-rest/v2/vouchers',
                    headers=headers,
                    files=files,
                    cookies=new_cookie
                )
        else:
            print("Failed to refresh cookie.")

    if response.status_code == 200:
        print(f"Document uploaded successfully, has lexoffice UUID {response.json().get('id')}")
    else:
        print("Request failed with status code:", response.status_code)

    return response

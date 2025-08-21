import os
import requests
import urllib.parse
from time import sleep

LEXOFFICE_BASE_URL = "https://app.lexware.de"
_session = None

def get_session(username=None, password=None):
    global _session
    if _session is None:
        _session = requests.Session()
        if username and password:
            url = urllib.parse.urljoin(
                LEXOFFICE_BASE_URL,
                'janus/janus-rest/public/login/web/v100/authenticate'
            )
            payload = {"username": username, "password": password}
            response = _session.post(url, json=payload)
            if response.status_code != 200:
                print(f"Error creating session cookie: {response.status_code}")
                _session = None
    return _session

def upload_voucher(filepath, username=None, password=None):
    filename = os.path.basename(filepath)
    print(f"Got filename {filename} to upload")

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

    response = post_file(session)

    if response.status_code == 401 and username and password:
        print("Unauthorized. Refreshing session...")
        global _session
        _session = None
        session = get_session(username, password)
        response = post_file(session)

    if response.status_code == 200:
        print(f"Document uploaded successfully, has lexoffice UUID {response.json().get('id')}")
    else:
        print("Request failed with status code:", response.status_code)

    return response

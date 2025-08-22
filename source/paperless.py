import os
import requests
import json
import urllib


DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", 10))  # seconds

def safe_json(response):
    """Try parsing JSON, else log error and return {}"""
    try:
        return response.json()
    except Exception as e:
        print(f"[Paperless] Invalid JSON response: {e}, content={response.text[:200]}")
        return {}


def search_documents(access_token, base_url, search_string):
    url = urllib.parse.urljoin(base_url, f"api/documents/?query=({search_string})")
    headers = {
        "Authorization": f"Token {access_token}",
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        if response.status_code != 200:
            print(f"[Paperless] Search HTTP {response.status_code}: {response.text[:200]}")
            return []

        search_data = safe_json(response)
        document_ids = [doc.get("id") for doc in search_data.get("results", [])]
        print(f"[Paperless] Search results: {document_ids}")
        return document_ids

    except requests.RequestException as e:
        print(f"[Paperless] Search connection error: {e}")
        return []


def filter_documents_by_tags(access_token, base_url, tags):
    tags_string = ",".join(str(tag) for tag in tags)
    url = urllib.parse.urljoin(base_url, f"api/documents/?tags__id__all={tags_string}")
    headers = {
        "Authorization": f"Token {access_token}",
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        if response.status_code != 200:
            print(f"[Paperless] Filter HTTP {response.status_code}: {response.text[:200]}")
            return []

        search_data = safe_json(response)
        document_ids = [doc.get("id") for doc in search_data.get("results", [])]
        print(f"[Paperless] Filter results: {document_ids}")
        return document_ids

    except requests.RequestException as e:
        print(f"[Paperless] Filter connection error: {e}")
        return []


def download_document(access_token, base_url, doc_id):
    url = urllib.parse.urljoin(base_url, f"api/documents/{doc_id}/download/")
    headers = {
        "Authorization": f"Token {access_token}",
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, stream=True, timeout=DEFAULT_TIMEOUT)
        if response.status_code == 200:
            document_binary = b''.join(response.iter_content(chunk_size=8192))
            print(f"[Paperless] Document #{doc_id} downloaded successfully ({len(document_binary)} bytes).")
            return document_binary
        else:
            print(f"[Paperless] Download failed HTTP {response.status_code}: {response.text[:200]}")
            return None

    except requests.RequestException as e:
        print(f"[Paperless] Download connection error: {e}")
        return None


def set_custom_field(access_token, base_url, document_id, field_id, field_value):
    url = f"{base_url}/api/documents/{document_id}/"
    headers = {
        "Authorization": f"Token {access_token}",
        "Content-Type": "application/json",
    }
    payload = json.dumps({
        "custom_fields": [{"value": field_value, "field": field_id}]
    })

    try:
        response = requests.patch(url, headers=headers, data=payload, timeout=DEFAULT_TIMEOUT)
        if response.status_code == 200:
            print(f"[Paperless] Custom field set on document #{document_id}.")
        else:
            print(f"[Paperless] Set custom field failed HTTP {response.status_code}: {response.text[:200]}")
    except requests.RequestException as e:
        print(f"[Paperless] Custom field connection error: {e}")


def remove_tag(access_token, base_url, document_id, tag_ids):
    url = urllib.parse.urljoin(base_url, f"api/documents/{document_id}/")
    headers = {
        "Authorization": f"Token {access_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        if response.status_code != 200:
            print(f"[Paperless] Fetch document failed HTTP {response.status_code}: {response.text[:200]}")
            return

        doc_data = safe_json(response)
        current_tags = doc_data.get("tags", [])
        new_tags = [tag for tag in current_tags if tag not in map(int, tag_ids)]

        payload = json.dumps({"tags": new_tags})
        patch_resp = requests.patch(url, headers=headers, data=payload, timeout=DEFAULT_TIMEOUT)
        if patch_resp.status_code == 200:
            print(f"[Paperless] Removed tag IDs {tag_ids} from document #{document_id}.")
        else:
            print(f"[Paperless] Remove tag failed HTTP {patch_resp.status_code}: {patch_resp.text[:200]}")

    except requests.RequestException as e:
        print(f"[Paperless] Remove tag connection error: {e}")

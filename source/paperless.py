import requests
import json
import urllib

def search_documents(access_token, base_url, search_string):
    url = urllib.parse.urljoin(base_url, f"api/documents/?query=({search_string})")
    headers = {
        "Authorization": f"Token {access_token}",
        "Accept": "application/json",
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            search_data = response.json()
            document_ids = search_data.get('all', [])
            print(f"Search Results: {document_ids}")
            return document_ids
        else:
            print(f"Search raised HTTP error: {response.status_code}")
    except Exception as e:
        print(f"Error connecting to paperless-ngx: {e}")

def filter_documents_by_tags(access_token, base_url, tags):
    tags_string = ",".join(str(tag) for tag in tags)
    url = urllib.parse.urljoin(base_url, f"api/documents/?tags__id__all={tags_string}")
    headers = {
        "Authorization": f"Token {access_token}",
        "Accept": "application/json",
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            search_data = response.json()
            document_ids = search_data.get('all', [])
            print(f"Search Results: {document_ids}")
            return document_ids
        else:
            print(f"Search raised HTTP error: {response.status_code}")
    except Exception as e:
        print(f"Error connecting to paperless-ngx: {e}")

def download_document(access_token, base_url, doc_id):
    url = urllib.parse.urljoin(base_url, f"api/documents/{doc_id}/download/")
    headers = {
        "Authorization": f"Token {access_token}",
        "Accept": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, stream=True)
        if response.status_code == 200:
            document_binary = b''.join(response.iter_content(chunk_size=8192))
            print(f"Document #{doc_id} downloaded successfully.")
            return document_binary
        else:
            print(f"Failed to download document. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error connecting to paperless-ngx: {e}")

def set_custom_field(access_token, base_url, document_id, field_id, field_value):
    url = f'{base_url}/api/documents/{document_id}/'
    headers = {
        "Authorization": f"Token {access_token}",
        "Content-Type": "application/json",
    }
    payload = json.dumps({
        "custom_fields": [
            {
                "value": field_value,
                "field": field_id
            }
        ]
    })
    try:
        requests.patch(url, headers=headers, data=payload)
    except Exception as e:
        print(f"Error connecting to paperless-ngx: {e}")

def remove_tag(access_token, base_url, document_id, tag_ids):
    url = urllib.parse.urljoin(base_url, f"api/documents/{document_id}/")
    headers = {
        "Authorization": f"Token {access_token}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            document_data = response.json()
            current_tags = document_data.get('tags', [])
            new_tags = [tag for tag in current_tags if tag not in map(int, tag_ids)]
            payload = json.dumps({"tags": new_tags})
            requests.patch(url, headers=headers, data=payload)
            print(f"Removed tag IDs {tag_ids} from document #{document_id}.")
        else:
            print(f"Failed to fetch document data. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error connecting to paperless-ngx: {e}")

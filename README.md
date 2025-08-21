# paperless-to-lexoffice

A synchronization tool that allows you to automatically sync selected documents from **paperless-ngx** into **lexoffice**.  
The sync is **unidirectional** (paperless-ngx ➝ lexoffice).

---

## 🚀 Features
- Sync documents from paperless-ngx to lexoffice automatically.  
- Tag-based workflow:  
  - Documents in the **inbox tag** are monitored.  
  - Adding the **lexoffice tag** triggers synchronization.  
- Runs in Docker for easy setup.  

---

## 📋 Prerequisites

Before running this service, prepare the following:

- A running **paperless-ngx** instance.  
- A **paperless-ngx API token** (the user must have the rights to view documents and edit tags).  
- A **lexoffice API token** (Public API usage is included in all lexoffice plans ✅).  
- Two tags in paperless-ngx:  
  - **Inbox Tag** → marks incoming documents.  
  - **Lexoffice Tag** → marks documents that should be synced.  

---

## ⚙️ Installation

1. Clone the repository and navigate into it.  
2. Go to the `docker` directory.  
3. Copy and edit the `docker-compose.env` file:
   - Add your tokens, URLs, and tag IDs.  
4. Start the container:
   ```bash
   docker-compose up -d

## 🔧 Environment Variables

You can configure the service with the following environment variables in `docker/docker-compose.env`:

### Polling

```ini
POLLING_INTERVAL=60
```

Interval in seconds to check for new documents.

### Paperless-ngx settings

```ini
PAPERLESS_TOKEN="TOKEN"                 # Your paperless-ngx API token
PAPERLESS_URL="http://192.168.0.5:8000" # URL of your paperless-ngx instance
INBOX_TAG_ID=1                          # Tag ID used for the inbox
LEXOFFICE_TAG_ID=42                     # Tag ID for documents to sync with lexoffice
```

### Lexoffice settings

```ini
LEXOFFICE_USERNAME="adalovelace"        # Your lexoffice username
LEXOFFICE_PASSWORD="ilovecookies"       # Your lexoffice password
```

## ⚠️ Limitations

- This tool is still in an early development stage.
- It has mainly been tested in personal document management setups.
- Feedback, bug reports, and contributions are very welcome!

## 📄 Example docker-compose.yml

```yaml
version: "3.8"
services:
  paperless-to-lexoffice:
    image: your-image-name:latest
    env_file:
      - docker-compose.env
    restart: unless-stopped
````

import os
import asyncio
import paperless
import lexoffice

# Config
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", 60))
PAPERLESS_TOKEN = os.getenv('PAPERLESS_TOKEN')
PAPERLESS_URL = os.getenv('PAPERLESS_URL')
INBOX_TAG_ID = os.getenv('INBOX_TAG_ID')
LEXOFFICE_TAG_ID = os.getenv('LEXOFFICE_TAG_ID')
LEXOFFICE_USERNAME = os.getenv('LEXOFFICE_USERNAME')
LEXOFFICE_PASSWORD = os.getenv('LEXOFFICE_PASSWORD')
PAPERLESS_ADD_VOUCHER_URL = bool(os.getenv('PAPERLESS_ADD_VOUCHER_URL', 'True'))

TMP_DIR = "tmp"
LOCK_FILE = 'script.lock'

LEXOFFICE_VOUCHER_PREVIEW_URL = "https://app.lexware.de/vouchers#!/VoucherList/Invoice/"

def create_lock():
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))

def remove_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

def is_locked():
    return os.path.exists(LOCK_FILE)

async def sync_paperless_to_lexoffice():
    if is_locked():
        print("[Sync] Script is already running. Exiting.")
        return

    create_lock()
    try:
        print("[Sync] Checking for new documents in paperless-ngx tagged for upload...")
        document_ids = paperless.filter_documents_by_tags(
            PAPERLESS_TOKEN, PAPERLESS_URL, [INBOX_TAG_ID, LEXOFFICE_TAG_ID]
        )

        if document_ids:
            os.makedirs(TMP_DIR, exist_ok=True)
            for doc_id in document_ids:
                file_content = paperless.download_document(PAPERLESS_TOKEN, PAPERLESS_URL, doc_id)
                filepath = os.path.join(TMP_DIR, f"{doc_id}.pdf")
                with open(filepath, "wb") as file:
                    file.write(file_content)

                lexoffice_document_uuid = lexoffice.upload_voucher(
                    filepath,
                    username=LEXOFFICE_USERNAME,
                    password=LEXOFFICE_PASSWORD
                )

                os.remove(filepath)

                if lexoffice_document_uuid:
                    print("[Sync] Upload successful. Deleting file from tmp...")
                    paperless.remove_tag(PAPERLESS_TOKEN, PAPERLESS_URL, doc_id, [LEXOFFICE_TAG_ID])
                    paperless.set_custom_field(PAPERLESS_TOKEN, PAPERLESS_URL, doc_id, "lexoffice_document_uuid", f"{LEXOFFICE_VOUCHER_PREVIEW_URL}{lexoffice_document_uuid}")
                else:
                    print(f"[Sync] Upload not successful. Deleting file from tmp as it gets downloaded in the next cycle.")

    except Exception as e:
        print(f"[Sync] An error occurred: {e}")
    finally:
        remove_lock()

async def periodic_main(interval_seconds):
    while True:
        await sync_paperless_to_lexoffice()
        await asyncio.sleep(interval_seconds)

def main():
    asyncio.run(periodic_main(POLLING_INTERVAL))

if __name__ == "__main__":
    main()

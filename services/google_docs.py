from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
]

SERVICE_ACCOUNT_FILE = "config/credentials/google-service-account.json"


def get_docs_service():
    credentials = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )

    return build("docs", "v1", credentials=credentials)


def extract_text_from_doc(document: dict) -> str:
    text_parts = []

    for element in document.get("body", {}).get("content", []):
        paragraph = element.get("paragraph")
        if not paragraph:
            continue

        for item in paragraph.get("elements", []):
            text_run = item.get("textRun")
            if text_run:
                text_parts.append(text_run.get("content", ""))

    return "".join(text_parts).strip()


def read_google_doc_text(document_id: str) -> str:
    service = get_docs_service()
    document = service.documents().get(documentId=document_id).execute()
    return extract_text_from_doc(document)
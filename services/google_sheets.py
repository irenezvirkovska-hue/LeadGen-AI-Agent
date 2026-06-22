import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SERVICE_ACCOUNT_FILE = "config/credentials/google-service-account.json"


def get_google_client():
    credentials = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )

    return gspread.authorize(credentials)

SPREADSHEET_NAME = "Good Fit Not Fit"


def get_spreadsheet():
    client = get_google_client()
    return client.open_by_url("https://docs.google.com/spreadsheets/d/1Rl56Y8m0pbrz7LjmxWcHq_ph7Bi9fPvOornXNFXpD58/edit?gid=0#gid=0")


def test_connection():
    spreadsheet = get_spreadsheet()

    good_fit_sheet = spreadsheet.worksheet("Good Fit")
    not_fit_sheet = spreadsheet.worksheet("Not Fit")

    return {
        "spreadsheet_title": spreadsheet.title,
        "good_fit_title": good_fit_sheet.title,
        "not_fit_title": not_fit_sheet.title,
    }
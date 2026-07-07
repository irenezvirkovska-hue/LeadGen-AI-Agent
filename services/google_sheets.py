from datetime import datetime

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SERVICE_ACCOUNT_FILE = "config/credentials/google-service-account.json"

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1Rl56Y8m0pbrz7LjmxWcHq_ph7Bi9fPvOornXNFXpD58/edit?gid=0#gid=0"


def get_credentials():
    if "google_service_account" in st.secrets:
        service_account_info = dict(st.secrets["google_service_account"])
        return Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES,
        )

    return Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )


def get_google_client():
    credentials = get_credentials()
    return gspread.authorize(credentials)


def get_spreadsheet():
    client = get_google_client()
    return client.open_by_url(SPREADSHEET_URL)


def test_connection():
    spreadsheet = get_spreadsheet()

    good_fit_sheet = spreadsheet.worksheet("Good Fit")
    not_fit_sheet = spreadsheet.worksheet("Not Fit")

    return {
        "spreadsheet_title": spreadsheet.title,
        "good_fit_title": good_fit_sheet.title,
        "not_fit_title": not_fit_sheet.title,
    }


def append_company_result(data: dict):
    spreadsheet = get_spreadsheet()

    target_sheet = data.get("target_sheet", "Not Fit")

    if target_sheet not in ["Good Fit", "Not Fit"]:
        target_sheet = "Not Fit"

    worksheet = spreadsheet.worksheet(target_sheet)

    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        data.get("company_name") or "",
        data.get("website") or "",
        data.get("linkedin") or "",
        data.get("company_size") or "",
        data.get("job_title") or "",
    ]

    worksheet.append_row(row)

    return target_sheet
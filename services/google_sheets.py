from datetime import datetime

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SERVICE_ACCOUNT_FILE = "config/credentials/google-service-account.json"

RESULT_HEADERS = [
    "Дата і час",
    "Назва компанії",
    "Website",
    "LinkedIn",
    "Розмір компанії",
    "Вакансія",
    "ICP Match",
    "Причина",
]


def get_credentials():
    if "google_service_account" in st.secrets:
        return Credentials.from_service_account_info(
            dict(st.secrets["google_service_account"]),
            scopes=SCOPES,
        )

    return Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )


def get_google_client():
    credentials = get_credentials()
    return gspread.authorize(credentials)


def get_spreadsheet(spreadsheet_id: str):
    client = get_google_client()
    return client.open_by_key(spreadsheet_id)


def test_connection(spreadsheet_id: str):
    spreadsheet = get_spreadsheet(spreadsheet_id)

    good_fit_sheet = spreadsheet.worksheet("Good Fit")
    not_fit_sheet = spreadsheet.worksheet("Not Fit")

    return {
        "spreadsheet_title": spreadsheet.title,
        "good_fit_title": good_fit_sheet.title,
        "not_fit_title": not_fit_sheet.title,
    }


def ensure_headers(worksheet) -> None:
    if not worksheet.row_values(1):
        worksheet.append_row(RESULT_HEADERS)


def append_company_result(
    data: dict,
    spreadsheet_id: str,
    result_schema: str = "extended",
):
    spreadsheet = get_spreadsheet(spreadsheet_id)

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

    if result_schema == "extended":
        ensure_headers(worksheet)
        row.extend(
            [
                data.get("icp_match") or "",
                data.get("short_reason_ua") or "",
            ]
        )

    worksheet.append_row(row)

    return target_sheet

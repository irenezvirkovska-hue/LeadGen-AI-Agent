import json
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from services.google_sheets import append_company_result
from services.google_docs import read_google_doc_text


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


TEXTS = {
    "title": "LeadGen AI Agent / AI-агент для лідогенерації",
    "caption": "MVP Sprint 2 - Structured JSON extraction / Структуроване витягування даних у JSON",
    "input_label": "Paste job/company text here / Встав текст вакансії або компанії сюди",
    "placeholder": (
        "Paste company website info, LinkedIn info, company size, job title, and job description here...\n\n"
        "Встав сюди інформацію про сайт компанії, LinkedIn, розмір компанії, назву вакансії та опис вакансії..."
    ),
    "button": "Analyze / Аналізувати",
    "warning": "Please paste some text first. / Спочатку встав текст.",
    "spinner": "Analyzing with OpenAI... / Аналізую через OpenAI...",
    "result_header": "Extracted Result / Витягнутий результат",
    "raw_json": "Raw JSON / Сирий JSON",
    "error_header": "Error / Помилка",
}


FIELD_LABELS_UA = {
    "company_name": "Назва компанії",
    "website": "Сайт",
    "linkedin": "LinkedIn",
    "company_size": "Розмір компанії",
    "job_title": "Назва вакансії",
    "icp_match": "ICP Match",
    "target_sheet": "Вкладка Google Sheets",
    "short_reason_ua": "Коротка причина",
}

def load_icp():
    icp_path = Path("config/icps/default.json")

    with open(icp_path, "r", encoding="utf-8") as file:
        return json.load(file)
    
def load_icp_text():
    doc_id = "147cjnGlhGr1vbOsTPHYGJq427jd4HBU8cCQUSwRmOdQ"
    return read_google_doc_text(doc_id)
    

def extract_company_data(raw_text: str, icp: dict) -> dict:
    prompt = f"""
    ICP Configuration:

{icp}

Analyze the company according to this ICP.
Your task is not only to extract information.

Use the ICP configuration to understand:
- what company types are considered a fit;
- what technologies matter;
- what countries are allowed;
- what company sizes are preferred;
- who the target decision makers are;
- what pain points are relevant.

Use this knowledge when extracting data.
Do not invent information.
Only extract facts supported by the provided text.
Explain the verdict in natural Ukrainian, using only facts present in the vacancy or directly implied by the ICP.
Never invent information that is not supported by the provided text.
You are a data extraction assistant.

Extract the following fields from the provided job/company text:

1. company_name
2. website
3. linkedin
4. company_size
5. job_title
6. icp_match
7. target_sheet
8. short_reason_ua

Rules:
- Return ONLY valid JSON.
- Do not add explanations.
- Do not add markdown.
- If a value is not present, use null.
- Do not invent website, LinkedIn, or company size.
- You may infer company_name and job_title only if they are clearly mentioned in the text.
- If company_name is mentioned in company footer, privacy notice, job board text, or repeated company description, extract it.
- Do not say "can be found by searching".
- The JSON keys must be exactly:
  company_name, website, linkedin, company_size, job_title
  For icp_match, return only one of:
- "Yes"
- "No"
- "Unknown"

For target_sheet, return only one of:
- "Good Fit"
- "Not Fit"

If icp_match is "Yes", target_sheet must be "Good Fit".
If icp_match is "No" or "Unknown", target_sheet must be "Not Fit".

For short_reason_ua, write one short sentence in Ukrainian explaining the verdict.

Text:
{raw_text}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    content = response.output_text.strip()
    return json.loads(content)


def show_result(data: dict) -> None:
    for key, label in FIELD_LABELS_UA.items():
        value = data.get(key)
        if value is None or value == "":
            value = "Не знайдено"
        st.write(f"**{label}:** {value}")


st.set_page_config(page_title="LeadGen AI Agent", page_icon="🤖")

st.title(TEXTS["title"])
st.caption(TEXTS["caption"])

icp = load_icp_text()

st.info("Активний ICP: Google Doc")


raw_text = st.text_area(
    TEXTS["input_label"],
    height=350,
    placeholder=TEXTS["placeholder"],
)

if st.button(TEXTS["button"]):

    print("1. Натиснули Analyze")

    if not raw_text.strip():

        st.warning(TEXTS["warning"])

    else:

        print("2. Текст є, починаємо")

        try:

            with st.spinner(TEXTS["spinner"]):

                print("3. Перед OpenAI")

                extracted_data = extract_company_data(raw_text, icp)

                print("4. OpenAI відповів")
                st.subheader(TEXTS["result_header"])
                show_result(extracted_data)
                saved_sheet = append_company_result(extracted_data)
                st.success(f"Збережено у вкладку Google Sheets: {saved_sheet}")

                with st.expander(TEXTS["raw_json"]):
                    st.json(extracted_data)
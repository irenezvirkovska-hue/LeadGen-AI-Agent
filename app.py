import json
import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI


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
}


def extract_company_data(raw_text: str) -> dict:
    prompt = f"""
You are a data extraction assistant.

Extract the following fields from the provided job/company text:

1. company_name
2. website
3. linkedin
4. company_size
5. job_title

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

raw_text = st.text_area(
    TEXTS["input_label"],
    height=350,
    placeholder=TEXTS["placeholder"],
)

if st.button(TEXTS["button"]):
    if not raw_text.strip():
        st.warning(TEXTS["warning"])
    else:
        try:
            with st.spinner(TEXTS["spinner"]):
                extracted_data = extract_company_data(raw_text)

            st.subheader(TEXTS["result_header"])
            show_result(extracted_data)

            with st.expander(TEXTS["raw_json"]):
                st.json(extracted_data)

        except json.JSONDecodeError:
            st.error("OpenAI returned invalid JSON. / OpenAI повернув некоректний JSON.")
            st.write("Raw response could not be parsed. / Сиру відповідь не вдалося розпарсити.")
        except Exception as error:
            st.error(TEXTS["error_header"])
            st.write(str(error))
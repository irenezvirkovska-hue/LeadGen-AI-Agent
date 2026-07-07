import base64
import json
import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from services.google_docs import read_google_doc_text
from services.google_sheets import append_company_result


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ICP_DOC_ID = "147cjnGlhGr1vbOsTPHYGJq427jd4HBU8cCQUSwRmOdQ"

TEXTS = {
    "title": "LeadGen AI Agent / AI-агент для лідогенерації",
    "caption": "ICP from Google Doc / ICP з Google Docs",
    "input_label": "Paste job/company text here / Встав текст вакансії або компанії сюди",
    "placeholder": (
        "Paste company website info, LinkedIn info, company size, job title, and job description here...\n\n"
        "Встав сюди інформацію про сайт компанії, LinkedIn, розмір компанії, назву вакансії та опис вакансії..."
    ),
    "button": "Analyze / Аналізувати",
    "new_company_button": "Analyze new company / Аналізувати нову компанію",
    "warning": "Встав текст або завантаж хоча б один скрін.",
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


@st.cache_data(ttl=600)
def load_icp_text() -> str:
    return read_google_doc_text(ICP_DOC_ID)


def image_to_data_url(uploaded_file) -> str:
    file_bytes = uploaded_file.getvalue()
    encoded = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{uploaded_file.type};base64,{encoded}"


def extract_company_data(raw_text: str, icp_text: str, image_files=None) -> dict:
    prompt = f"""
ICP Configuration:

{icp_text}

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
Only extract facts supported by the provided text or screenshots.
Explain the verdict in natural Ukrainian, using only facts present in the vacancy/company text, screenshots, or directly implied by the ICP.
Never invent information that is not supported by the provided text or screenshots.

You are a data extraction and ICP qualification assistant.

Extract the following fields from the provided job/company text or screenshots:

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
- Do not add explanations outside JSON.
- Do not add markdown.
- If a value is not present, use null.
- Do not invent website, LinkedIn, or company size.

- Carefully analyze both the pasted text and ALL uploaded screenshots.
- Treat screenshots as complementary evidence.
- If different screenshots contain different fields, combine the information into one final result.
- When analyzing a LinkedIn company About screenshot, inspect the main About/Overview block carefully.
- If any screenshot shows a field named "Website", extract the URL directly under that label into website.
- If any screenshot shows "Website" followed by a URL, this URL must be extracted even if it is not present in the pasted text.
- If a URL is visibly shown under labels like Website, Company website, or About, extract it into website.
- Do not confuse LinkedIn URL with company website: LinkedIn company page goes to linkedin, company website goes to website.
- If a LinkedIn company URL is visible in the pasted text or screenshot, extract it into linkedin.

- You may infer company_name and job_title only if they are clearly mentioned in the text or screenshots.
- If company_name is mentioned in company footer, privacy notice, job board text, screenshot, or repeated company description, extract it.
- Do not say "can be found by searching".

- The JSON keys must be exactly:
  company_name, website, linkedin, company_size, job_title, icp_match, target_sheet, short_reason_ua

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

    content_parts = [{"type": "input_text", "text": prompt}]

    if image_files:
        for image_file in image_files:
            image_url = image_to_data_url(image_file)
            content_parts.append({"type": "input_image", "image_url": image_url})

    response = client.responses.create(
        model="gpt-5.5",
        input=[  # type: ignore
            {
                "role": "user",
                "content": content_parts,
            }  # type: ignore
        ],
    )

    content = response.output_text.strip()
    return json.loads(content)


def show_result(data: dict) -> None:
    for key, label in FIELD_LABELS_UA.items():
        value = data.get(key)
        if value is None or value == "":
            value = "Не знайдено"
        st.write(f"**{label}:** {value}")


def show_saved_result() -> None:
    if st.session_state.last_result is None:
        return

    st.subheader(TEXTS["result_header"])
    show_result(st.session_state.last_result)

    if st.session_state.last_saved_sheet:
        st.success(
            f"Збережено у вкладку Google Sheets: {st.session_state.last_saved_sheet}"
        )

    with st.expander(TEXTS["raw_json"]):
        st.json(st.session_state.last_result)

    if st.button(TEXTS["new_company_button"]):
        st.session_state.last_result = None
        st.session_state.last_saved_sheet = None
        st.session_state.text_area_key += 1
        st.session_state.uploader_key += 1
        st.rerun()


st.set_page_config(page_title="LeadGen AI Agent", page_icon="🤖")

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "last_saved_sheet" not in st.session_state:
    st.session_state.last_saved_sheet = None

if "text_area_key" not in st.session_state:
    st.session_state.text_area_key = 0

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

st.title(TEXTS["title"])
st.caption(TEXTS["caption"])

try:
    icp_text = load_icp_text()
    st.info("Активний ICP: Google Doc")
except Exception as error:
    icp_text = ""
    st.error("Не вдалося прочитати ICP з Google Doc.")
    st.write(str(error))

raw_text = st.text_area(
    TEXTS["input_label"],
    height=350,
    placeholder=TEXTS["placeholder"],
    key=f"input_text_{st.session_state.text_area_key}",
)

uploaded_images = st.file_uploader(
    "Upload screenshots / Завантаж скріни або фото",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
    key=f"uploaded_images_{st.session_state.uploader_key}",
)

if st.button(TEXTS["button"]):
    if not raw_text.strip() and not uploaded_images:
        st.warning(TEXTS["warning"])
    elif not icp_text.strip():
        st.error("ICP порожній або не завантажився з Google Doc.")
    else:
        try:
            with st.spinner(TEXTS["spinner"]):
                extracted_data = extract_company_data(
                    raw_text=raw_text,
                    icp_text=icp_text,
                    image_files=uploaded_images,
                )

            saved_sheet = append_company_result(extracted_data)

            st.session_state.last_result = extracted_data
            st.session_state.last_saved_sheet = saved_sheet

            st.rerun()

        except json.JSONDecodeError:
            st.error("OpenAI повернув некоректний JSON.")
        except Exception as error:
            st.error(TEXTS["error_header"])
            st.write(str(error))

show_saved_result()
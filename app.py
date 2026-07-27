import base64
import json
import os
from io import BytesIO
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageFilter, ImageOps
from services.google_docs import read_google_doc_text
from services.google_sheets import append_company_result


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ICP_CATALOG_PATH = Path("config/icps/catalog.json")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
MAX_IMAGE_DIMENSION = 1600
MAX_OUTPUT_TOKENS = 1200
AUTO_CROP_MIN_WIDTH = 1200
AUTO_CROP_MIN_HEIGHT = 800

LEAD_QUALIFICATION_FORMAT = {
    "type": "json_schema",
    "name": "lead_qualification",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "company_name": {"type": ["string", "null"]},
            "website": {"type": ["string", "null"]},
            "linkedin": {"type": ["string", "null"]},
            "company_size": {"type": ["string", "null"]},
            "job_title": {"type": ["string", "null"]},
            "icp_match": {
                "type": "string",
                "enum": ["Yes", "No", "Unknown"],
            },
            "short_reason_ua": {"type": "string"},
        },
        "required": [
            "company_name",
            "website",
            "linkedin",
            "company_size",
            "job_title",
            "icp_match",
            "short_reason_ua",
        ],
        "additionalProperties": False,
    },
}

TEXTS = {
    "title": "LeadGen AI Agent / AI-агент для лідогенерації",
    "caption": "Select ICP from Google Docs / Обери ICP із Google Docs",
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


@st.cache_data
def load_icp_catalog() -> dict:
    with ICP_CATALOG_PATH.open("r", encoding="utf-8") as file:
        catalog = json.load(file)

    items = catalog.get("items", [])
    if not items:
        raise ValueError("Список ICP порожній.")

    required_fields = {
        "key",
        "label",
        "document_id",
        "spreadsheet_id",
        "result_schema",
    }
    for item in items:
        if not required_fields.issubset(item):
            raise ValueError("Некоректна конфігурація ICP.")
        if item["result_schema"] not in {"legacy", "extended"}:
            raise ValueError("Невідомий формат таблиці результатів.")

    keys = [item["key"] for item in items]
    if len(keys) != len(set(keys)):
        raise ValueError("Ключі ICP мають бути унікальними.")

    if catalog.get("default") not in keys:
        raise ValueError("ICP за замовчуванням відсутній у списку.")

    return catalog


@st.cache_data(ttl=600)
def load_icp_text(document_id: str) -> str:
    return read_google_doc_text(document_id)


def auto_crop_uniform_side_margins(image: Image.Image) -> Image.Image:
    """Crop large low-detail side margins while keeping the full image height."""
    if (
        image.width < AUTO_CROP_MIN_WIDTH
        or image.height < AUTO_CROP_MIN_HEIGHT
    ):
        return image

    preview = image.copy()
    preview.thumbnail((1000, 1000), Image.Resampling.BILINEAR)

    analysis_band = preview.crop(
        (
            0,
            round(preview.height * 0.18),
            preview.width,
            round(preview.height * 0.85),
        )
    )
    edges = analysis_band.convert("L").filter(ImageFilter.FIND_EDGES)
    edges = edges.crop((2, 2, edges.width - 2, edges.height - 2))
    strong_edges = edges.point(lambda value: 255 if value >= 24 else 0)
    column_density = strong_edges.resize(
        (strong_edges.width, 1),
        Image.Resampling.BOX,
    )

    active_columns = [
        index + 2
        for index, density in enumerate(column_density.getdata())
        if density >= 3
    ]
    if not active_columns:
        return image

    left_preview = active_columns[0]
    right_preview = active_columns[-1] + 1
    content_width = right_preview - left_preview

    # Crop only when both the detected content and the saving are substantial.
    if (
        content_width < preview.width * 0.15
        or content_width > preview.width * 0.88
    ):
        return image

    scale = image.width / preview.width
    padding = max(24, round(content_width * scale * 0.06))
    left = max(0, round(left_preview * scale) - padding)
    right = min(image.width, round(right_preview * scale) + padding)

    return image.crop((left, 0, right, image.height))


def image_to_data_url(uploaded_file) -> str:
    image = Image.open(BytesIO(uploaded_file.getvalue()))
    image = ImageOps.exif_transpose(image).convert("RGB")
    image = auto_crop_uniform_side_margins(image)
    image.thumbnail(
        (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION),
        Image.Resampling.LANCZOS,
    )

    output = BytesIO()
    image.save(output, format="JPEG", quality=90, optimize=True)
    encoded = base64.b64encode(output.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def extract_usage_stats(response) -> dict:
    usage = response.usage
    input_details = getattr(usage, "input_tokens_details", None)

    return {
        "model": getattr(response, "model", OPENAI_MODEL),
        "input_tokens": getattr(usage, "input_tokens", 0),
        "output_tokens": getattr(usage, "output_tokens", 0),
        "cached_tokens": getattr(input_details, "cached_tokens", 0),
        "total_tokens": getattr(usage, "total_tokens", 0),
    }


def extract_company_data(
    raw_text: str,
    icp_text: str,
    icp_key: str,
    image_files=None,
) -> tuple[dict, dict]:
    prompt = f"""
Extract company data and qualify it against the ICP below.
Use only facts supported by the text or screenshots; use null when a field is absent.
Combine evidence from all inputs without inventing values.
Keep the company website separate from its LinkedIn URL.
Inspect visible Website fields and the main LinkedIn About/Overview content carefully.
Set icp_match from the ICP criteria and write one concise Ukrainian sentence in
short_reason_ua explaining the verdict.

ICP:
{icp_text}

Company or vacancy text:
{raw_text}
"""

    content_parts = [{"type": "input_text", "text": prompt}]

    if image_files:
        for image_file in image_files:
            image_url = image_to_data_url(image_file)
            content_parts.append({"type": "input_image", "image_url": image_url})

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=[  # type: ignore
            {
                "role": "user",
                "content": content_parts,
            }  # type: ignore
        ],
        max_output_tokens=MAX_OUTPUT_TOKENS,
        prompt_cache_key=f"leadgen:{icp_key}:v1",
        reasoning={"effort": "low"},
        text={"format": LEAD_QUALIFICATION_FORMAT},
    )

    content = response.output_text.strip()
    if not content:
        incomplete_details = getattr(response, "incomplete_details", None)
        reason = getattr(incomplete_details, "reason", None)
        if reason == "max_output_tokens":
            raise RuntimeError(
                "OpenAI не встиг сформувати відповідь у межах ліміту токенів. "
                "Спробуйте ще раз."
            )
        raise RuntimeError("OpenAI не повернув текстову відповідь. Спробуйте ще раз.")

    extracted_data = json.loads(content)
    extracted_data["target_sheet"] = (
        "Good Fit" if extracted_data["icp_match"] == "Yes" else "Not Fit"
    )
    return extracted_data, extract_usage_stats(response)


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

    if st.session_state.last_icp_label:
        st.info(f"Аналіз виконано за ICP: {st.session_state.last_icp_label}")

    show_result(st.session_state.last_result)

    if st.session_state.last_saved_sheet:
        st.success(
            f"Збережено в таблицю для {st.session_state.last_icp_label}, "
            f"вкладка: {st.session_state.last_saved_sheet}"
        )

    if st.session_state.last_usage:
        st.subheader("Використання токенів")
        st.caption(f"Модель: {st.session_state.last_usage.get('model', '—')}")
        input_column, output_column, cached_column, total_column = st.columns(4)
        input_column.metric(
            "Вхідні",
            st.session_state.last_usage["input_tokens"],
        )
        output_column.metric(
            "Вихідні",
            st.session_state.last_usage["output_tokens"],
        )
        cached_column.metric(
            "З кешу",
            st.session_state.last_usage["cached_tokens"],
        )
        total_column.metric(
            "Усього",
            st.session_state.last_usage["total_tokens"],
        )

    with st.expander(TEXTS["raw_json"]):
        st.json(st.session_state.last_result)

    if st.button(TEXTS["new_company_button"]):
        st.session_state.last_result = None
        st.session_state.last_saved_sheet = None
        st.session_state.last_icp_label = None
        st.session_state.last_usage = None
        st.session_state.text_area_key += 1
        st.session_state.uploader_key += 1
        st.rerun()


st.set_page_config(page_title="LeadGen AI Agent", page_icon="🤖")

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "last_saved_sheet" not in st.session_state:
    st.session_state.last_saved_sheet = None

if "last_icp_label" not in st.session_state:
    st.session_state.last_icp_label = None

if "last_usage" not in st.session_state:
    st.session_state.last_usage = None

if "text_area_key" not in st.session_state:
    st.session_state.text_area_key = 0

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

st.title(TEXTS["title"])
st.caption(TEXTS["caption"])

try:
    icp_catalog = load_icp_catalog()
    icp_items = icp_catalog["items"]
    icp_by_key = {item["key"]: item for item in icp_items}
    icp_keys = [item["key"] for item in icp_items]
    default_index = icp_keys.index(icp_catalog["default"])

    selected_icp_key = st.selectbox(
        "Оберіть ICP / Select ICP",
        options=icp_keys,
        index=default_index,
        format_func=lambda key: icp_by_key[key]["label"],
        key="selected_icp_key",
    )
    selected_icp = icp_by_key[selected_icp_key]
    icp_text = load_icp_text(selected_icp["document_id"])
    st.info(f"Активний ICP: {selected_icp['label']}")
except Exception as error:
    selected_icp = None
    icp_text = ""
    st.error("Не вдалося завантажити вибраний ICP.")
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
st.caption(
    "Порожні бокові поля обрізаються автоматично. "
    "Для меншої вартості завантажуй лише 1–2 потрібні скриншоти."
)

if len(uploaded_images) > 3:
    st.warning(
        "Завантажено понад 3 скриншоти. Це суттєво збільшує кількість токенів."
    )

if st.button(TEXTS["button"]):
    if not raw_text.strip() and not uploaded_images:
        st.warning(TEXTS["warning"])
    elif not icp_text.strip():
        st.error("ICP порожній або не завантажився з Google Doc.")
    else:
        try:
            with st.spinner(TEXTS["spinner"]):
                extracted_data, usage_stats = extract_company_data(
                    raw_text=raw_text,
                    icp_text=icp_text,
                    icp_key=selected_icp["key"],
                    image_files=uploaded_images,
                )

            saved_sheet = append_company_result(
                extracted_data,
                spreadsheet_id=selected_icp["spreadsheet_id"],
                result_schema=selected_icp["result_schema"],
            )

            st.session_state.last_result = extracted_data
            st.session_state.last_saved_sheet = saved_sheet
            st.session_state.last_icp_label = selected_icp["label"]
            st.session_state.last_usage = usage_stats

            st.rerun()

        except json.JSONDecodeError:
            st.error(
                "Відповідь OpenAI обірвалася або мала некоректний формат. "
                "Спробуйте ще раз."
            )
        except Exception as error:
            st.error(TEXTS["error_header"])
            st.write(str(error))

show_saved_result()

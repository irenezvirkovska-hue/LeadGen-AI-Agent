import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


st.set_page_config(page_title="LeadGen AI Agent", page_icon="🤖")

st.title("LeadGen AI Agent")
st.caption("MVP Sprint 1 - AI connection test")

raw_text = st.text_area(
    "Paste job/company text here",
    height=300,
    placeholder="Paste company website info, LinkedIn info, company size, job title, and job description here...",
)

if st.button("Analyze"):
    if not raw_text.strip():
        st.warning("Please paste some text first.")
    else:
        with st.spinner("Analyzing with OpenAI..."):
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=f"""
Extract the following fields from the text:
- Company Name
- Website
- LinkedIn
- Company Size
- Job Title

Return the result as a simple readable list.

Text:
{raw_text}
"""
            )

        st.subheader("Extracted Result")
        st.write(response.output_text)
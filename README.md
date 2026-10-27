# LeadGen AI Agent

A Streamlit application that helps qualify companies and job opportunities against a selected Ideal Customer Profile (ICP). It analyzes pasted text and screenshots with OpenAI, loads qualification criteria from Google Docs, and saves structured results to Google Sheets.

Built by **Iryna Zvirkovska** to support practical lead generation workflows.

## Features

- **Three configurable ICP profiles:** .NET Hiring, Angular Hiring, and React Hiring.
- **Google Docs integration:** qualification criteria are loaded from the document associated with the selected profile and cached for 10 minutes.
- **Text and screenshot input:** combine company information, LinkedIn details, and job descriptions in one analysis.
- **Image preparation:** correct image orientation, detect and crop large low-detail side margins, and resize images before submission.
- **Structured output:** extract company name, website, LinkedIn URL, company size, job title, ICP match, and a concise explanation in Ukrainian.
- **Google Sheets integration:** save each result to the selected profile's spreadsheet, under `Good Fit` or `Not Fit`.
- **Token usage display:** show input, output, cached, and total tokens reported by the API.
- **Bilingual interface:** English and Ukrainian labels.

## Workflow

1. Select an ICP profile.
2. The application reads its criteria from Google Docs.
3. Paste company or vacancy information and/or upload PNG or JPEG screenshots.
4. Click **Analyze**.
5. Review the extracted information and qualification explanation.
6. The result is automatically appended to the corresponding Google Sheets worksheet.
7. Click **Analyze new company** to clear the previous input and result.

The application evaluates the supplied evidence. It does not autonomously browse websites or scrape LinkedIn.

## Technology Stack

Python · Streamlit · OpenAI Responses API · Pillow · Google Docs API · Google Sheets / gspread · Google service-account authentication · python-dotenv

The default model is `gpt-5-mini`; it can be changed through `OPENAI_MODEL`.

## Project Structure

```text
LeadGen-AI-Agent/
├── app.py                       # Streamlit UI, image preparation, LLM analysis
├── requirements.txt
├── config/
│   ├── icps/
│   │   └── catalog.json          # ICP profiles and document/spreadsheet mappings
│   ├── credentials/             # Local service-account JSON; excluded from Git
│   └── ...                      # Additional configuration placeholders
├── services/
│   ├── google_docs.py           # Read ICP text from Google Docs
│   └── google_sheets.py         # Route and append results to Google Sheets
└── docs/                        # Reserved documentation placeholders
```

Some configuration and documentation files are currently empty placeholders. The active ICP catalog is `config/icps/catalog.json`; the analysis prompt and output schema are implemented in `app.py`.

## Local Setup

### 1. Install dependencies

Use a Python environment compatible with the pinned packages.

```bash
git clone https://github.com/irenezvirkovska-hue/LeadGen-AI-Agent.git
cd LeadGen-AI-Agent
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install Pillow
```

The application imports Pillow, but it is not explicitly listed in the current `requirements.txt`; the additional installation makes this dependency explicit for local setup.

### 2. Configure OpenAI

Create a local `.env` file:

```dotenv
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5-mini
```

A compatible OpenAI API account and model access are required. API calls may incur charges.

### 3. Configure Google access

Enable the Google Docs, Google Sheets, and Google Drive APIs in your Google Cloud project and create a service account.

For local use, save its credentials at:

```text
config/credentials/google-service-account.json
```

Alternatively, the application can read a `google_service_account` section from Streamlit secrets.

Share each ICP Google Doc with the service account as a viewer and each destination spreadsheet as an editor. Each spreadsheet must already contain worksheets named **Good Fit** and **Not Fit**.

Keep credentials out of version control. The existing `.gitignore` excludes `.env` and JSON files under `config/credentials/`. If using a local `.streamlit/secrets.toml` file, exclude it from Git before adding credentials; the current `.gitignore` does not explicitly cover that path.

### 4. Set up your ICP catalog

Replace the document and spreadsheet IDs in `config/icps/catalog.json` with resources you control. The IDs included in the repository do not grant access to the underlying resources.

Example catalog:

```json
{
  "default": "dotnet-hiring",
  "items": [
    {
      "key": "dotnet-hiring",
      "label": "ICP - .NET Hiring",
      "document_id": "YOUR_GOOGLE_DOC_ID",
      "spreadsheet_id": "YOUR_GOOGLE_SHEET_ID",
      "result_schema": "extended"
    }
  ]
}
```

Every profile requires a unique `key`, a `label`, a `document_id`, a `spreadsheet_id`, and a `result_schema`. The `default` value must match an existing profile key.

Supported result layouts:

| Layout | Columns written |
| --- | --- |
| `legacy` | Timestamp, company name, website, LinkedIn, company size, job title |
| `extended` | All legacy columns, plus ICP match and explanation |

The current catalog uses `legacy` for .NET and `extended` for Angular and React. Extended worksheets receive headers when their first row is empty.

### 5. Run

```bash
streamlit run app.py
```

## Qualification Output

| Field | Meaning |
| --- | --- |
| `company_name` | Company name found in the supplied evidence |
| `website` | Company website |
| `linkedin` | LinkedIn URL |
| `company_size` | Reported company size |
| `job_title` | Job title |
| `icp_match` | `Yes`, `No`, or `Unknown` |
| `short_reason_ua` | Concise qualification explanation in Ukrainian |

Missing extracted fields can be `null`. The prompt instructs the model to use supported facts and avoid inventing values, but results still require human review.

**Current routing:** `Yes` goes to `Good Fit`; both `No` and `Unknown` go to `Not Fit`. Treat `Unknown` as insufficient evidence, rather than a confirmed negative qualification.

## Current Limitations

- This is a focused, user-operated qualification tool; it does not implement an autonomous multi-agent or MCP workflow.
- ICP reading currently extracts top-level Google Docs paragraphs; table contents are not traversed.
- Results are saved automatically after analysis, without a separate approval step.
- There is no duplicate detection before appending a row.
- An API or Google Sheets error is displayed in the interface; automatic retries are not implemented.
- The token display reports usage counts, not monetary cost.
- Text, screenshots, and loaded ICP criteria are sent to OpenAI for analysis; extracted results are written to the configured Google spreadsheet. Use inputs you are authorized to process.
- This README documents the inspected implementation. A fresh end-to-end run with configured credentials has not been verified as part of this documentation update.

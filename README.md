# Patient Health Tracker

A small Flask + SQLite application that stores patient blood-test records and uses an external AI API (Google Gemini API) to generate a possible health-condition / risk remark for each record.

## Features
- Create, read, update and delete patient records
- Server-side validation (name, dd/mm/yyyy date of birth, email format, numeric blood values within plausible ranges, duplicate email detection)
- Persistent storage in SQLite (`patients.db`, created on first run)
- AI remarks generated only after a record passes validation; regenerated on edit when the date of birth or blood values change; "Re-run AI" button to retry if the API was unavailable

## Project structure
```
app.py            Flask routes and database access
validators.py     Input validation rules
ai_service.py     AI API integration
templates/        HTML templates (base, list/add form, edit form)
tests/            pytest suite covering the assignment's 10 test rows
```

## Run locally
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
export GEMINI_API_KEY=your-api-key   # Windows: set GEMINI_API_KEY=your-api-key
export GEMINI_MODEL=gemini-3.5-flash-lite   # optional, if the default model is busy (HTTP 503)
python app.py
```
Open http://127.0.0.1:5000. Without an API key, records still save and the Remarks column shows that the AI prediction is unavailable.

Run the tests (AI call is mocked): `python -m pytest -q`

## Validation rules
| Field | Rule |
|---|---|
| Full name | Required; letters, spaces, `.` `'` `-` only |
| Date of birth | dd/mm/yyyy (dd.mm.yyyy and dd-mm-yyyy are normalised to dd/mm/yyyy); must be a real date; not in the future |
| Email | Required; must match `name@domain.tld`; must be unique |
| Glucose / Haemoglobin / Cholesterol | Numeric and within plausible ranges (20-800 / 3-25 / 50-600) |

## Expected results for the assignment's test data
| # | Name | Result | Reason |
|---|---|---|---|
| 1 | Robyn Pears | Saved | Valid |
| 2 | John Hunter | Rejected | Email `hunter@gmail` has no top-level domain |
| 3 | Darryl Tim | Saved | Valid (AI should flag high haemoglobin / cholesterol) |
| 4 | Peter Larry | Rejected | 31.11.2001 is not a real date (November has 30 days) |
| 5 | Sam Kerr | Saved | Valid |
| 6 | Robyn Pears | Rejected | Duplicate of #1 (same email) |
| 7 | Madison XI | Saved | Valid |
| 8 | Kris Wu | Rejected | Birth date 19.10.2030 is in the future; email `Kris.wu.gmail.com` has no `@` |
| 9 | Tenille Singh | Saved | Valid |
| 10 | Prem Kumar | Saved | Valid |

The test data uses dots (28.01.1960). The app accepts `.`, `-` or `/` and stores dates as dd/mm/yyyy.

## API key
The key is read from the `GEMINI_API_KEY` environment variable. It is never stored in the code or the repository. Get a free key from Google AI Studio (https://aistudio.google.com).

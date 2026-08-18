# Tabula

Tabula is a financial claims and evidence ledger for recording assertions made in earnings calls, investor presentations, filings, and financial media. It connects the original statement to source material, later revisions, and observable outcomes without treating repetition as proof.

## Product model

| Record | Purpose |
| --- | --- |
| Claim | The attributable assertion being tracked, with company, status, owner, and confidence. |
| Source | The primary material that carries a claim, such as a filing, earnings call, presentation, or article. |
| Evidence | A source-linked excerpt, metric, artifact, or source reference attached to a claim. |
| Revision | A dated change from the previous claim wording, preserving the evolution of the assertion. |
| Outcome | A later checkpoint that records whether the observed result was pending, confirmed, mixed, or contradicted. |

## Features

Tabula provides a responsive web interface for an overview dashboard, searchable claims register, source archive, and claim detail workspaces. Each claim workspace contains an evidence trail, revision history, outcome checkpoints, and a visible separation between what was said and what later happened. A JSON API is available at `/api/claims` for integrations and scripted workflows.

## Requirements

Python 3.11 or newer is required. The application uses FastAPI, SQLAlchemy, Jinja2, SQLite by default, and Uvicorn for local serving.

## Local setup

```bash
git clone https://github.com/ak495867/Tabula.git
cd Tabula
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
uvicorn tabula.app:app --reload
```

Open `http://127.0.0.1:8000` in a browser. The SQLite database is created as `tabula.db` on first startup.

The command-line entrypoint is also available after installation:

```bash
tabula --reload
```

## Configuration

Tabula uses the `TABULA_DATABASE_URL` environment variable when a different SQLAlchemy-compatible database URL is needed. The default is `sqlite:///./tabula.db`.

```bash
export TABULA_DATABASE_URL='sqlite:///./data/tabula.db'
```

## API

The read endpoint returns all claims with evidence and outcome counts:

```bash
curl http://127.0.0.1:8000/api/claims
```

Claims can be created as JSON:

```bash
curl -X POST http://127.0.0.1:8000/api/claims \
  -H 'Content-Type: application/json' \
  -d '{"company":"Acme Holdings","title":"Margin expansion remains durable","statement":"Management expects operating margin to expand over the next two fiscal years.","confidence":60,"owner":"Research"}'
```

## Testing and quality checks

Run the test suite with:

```bash
pytest
```

Run the formatter and static checks with:

```bash
ruff check .
```

## Repository structure

```text
Tabula/
├── tabula/
│   ├── app.py
│   ├── cli.py
│   ├── database.py
│   ├── models.py
│   ├── static/
│   │   ├── app.js
│   │   └── styles.css
│   └── templates/
├── tests/
├── .gitignore
├── Dockerfile
├── LICENSE
├── README.md
└── pyproject.toml
```


# Zinvest AI Accountant

Zinvest AI Accountant is an AI that does the finance work of a small business in Uzbekistan instead of only talking about it.
The owner describes income and expenses in their own words; the AI turns them into records, analyses the business,
warns when the cash will run out and what to do, picks the best bank loan and writes a business plan with a 12-month forecast.
**Nothing changes until the owner presses "Approve"**, and every action, with its decision, is kept on a history page that
downloads as PDF or CSV.

The AI Accountant is part of [Zinvest](https://zinvest-kappa.vercel.app), a financial-literacy platform for young people and small
businesses in Uzbekistan (Russian, Uzbek and English).

## What the AI does, and what it needs permission for

| Step | The AI does on its own | Changes only after "Approve" |
|---|---|---|
| 1. Income and expenses | Reads the owner's free text ("July: bread 46 mln, rent 9 mln…") and proposes records | Adds the records to the books |
| 2. Analysis | Health check of the monthly figures: findings and 3–5 actions with their effect | Saves the report, adds the actions to the to-do list |
| 3. Money warning | "You will run out of money in 2 months — by 2026-12", and how to stretch the cash | Saves the forecast, adds the actions to the to-do list |
| 4. Bank loan | Compares small-business loans of Uzbek banks (Hamkorbank, Kapitalbank, Ipak Yuli, Aloqabank, NBU, MKBank) and explains the best | Saves the choice, adds "apply" to the to-do list |
| 5. Business plan | One-page plan with a 12-month forecast built from the owner's numbers | Saves the plan |

Numbers are never left to the model: averages, cash runway, loan payments (annuity) and the forecast are computed in code
(`backend/copilot/finance.py`, `backend/copilot/loans.py`); the AI reads text and explains. Its answers are checked before
anyone sees them — amounts must be real positive numbers from the text, a chosen loan must be one of the bank products in
the catalogue. Loan terms are the banks' advertised terms (October 2026) and are marked as indicative.

## How it is built

- **AI:** Google Gemini (`gemini-2.5-flash`, with automatic fallback to another model when one model's quota is used up),
  called through the official `google-genai` SDK with JSON output.
- **Backend:** Python 3.12, Django 6, PostgreSQL in production (Supabase), SQLite locally. The AI Accountant is the `copilot` app.
- **Frontend:** Vue 3, Vite, Tailwind CSS 4, vue-i18n (ru / uz / en).
- **How the website talks to the AI:** the browser only calls Zinvest's own REST API (`/api/copilot/...`, JWT auth). The
  server builds the prompt from the business's own records, calls Gemini, checks the answer and stores it as a *proposal*;
  `POST /api/copilot/actions/<id>/decide` with `approve` or `reject` is the only way it touches the business's data.
- **Safety:** per-user AI token quotas, API rate limits, no personal names sent to the model, the owner's data isolated per account.

## Install and start

You need Python 3.12+ and Node.js 20+.

```bash
# Backend (http://127.0.0.1:8000)
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt        # Windows: .venv\Scripts\pip install -r requirements.txt
cp ../.env.example ../.env                       # then put your GEMINI_API_KEY in ../.env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py import_units          # the 11-unit course (optional for the AI Accountant)
.venv/bin/python manage.py runserver

# Frontend (http://localhost:5173), in a second terminal
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, sign up, then **AI Accountant** in the left menu. Without a `GEMINI_API_KEY` the app still runs and
the AI steps answer that AI is not connected.

## Run the tests

```bash
# Simple tests of the AI Accountant logic (no database, no AI key), from the repository root
python -m unittest discover -s tests -t .

# The full suite: 277 tests, including the AI Accountant flow (proposal → approve/reject → history) with a mocked AI
cd backend
python manage.py test
python manage.py test copilot     # only the AI Accountant
```

## Test runs (`logs/`)

Four fictional organisations were run through all five steps in the real app (live Gemini), each proposal approved, and
the history page saved as PDF:

| File | Business | Result |
|---|---|---|
| `logs/test_bakery.pdf` | Non Uyi Bakery, Tashkent | Loses 10.3 mln UZS a month → "run out of money in 2 months"; loan: Hamkorbank |
| `logs/test_clothing.pdf` | Moda Line clothing shop, Samarkand | Loses 6.7 mln a month → 4.5 months; loan: Ipak Yuli Bank (self-employed) |
| `logs/test_itstudio.pdf` | Pixel Code Studio, Tashkent | Profitable (+24 mln a month), no warning; loan: Hamkorbank |
| `logs/test_nonprofit.pdf` | Yosh Kelajak Foundation (nonprofit), Bukhara | Loses 9 mln a month → "run out of money in 2 months"; loan: Hamkorbank |

## Documents (`docs/`)

- `docs/Technical_Documentation.pdf`: system architecture, the core algorithm (proposal → approval loop, the cash-flow
  warning, loan matching, the 12-month forecast) and the security design.
- `docs/Security_Self_Assessment.pdf`: the permission tiers and how they are enforced, the security controls, the
  known-risk list, and what was found and fixed during the assessment.

## Repository layout

```
backend/            Django project (copilot/ is the AI Accountant; accounts, ai_engine, startup, learning, …)
frontend/           Vue 3 app (src/views/Copilot.vue, src/views/CopilotHistory.vue, src/components/copilot/)
tests/              simple tests of the AI Accountant logic
logs/               the four test runs as PDF
docs/               technical documentation and security self-assessment
deploy/vercel/      how the app is bundled for Vercel
tools/units/        converter that turns the course PDFs into lessons
```

## Credits

- **Zinvest team** — Behruz and the Zinvest contributors. The first version of the frontend was started by **FizzyFocus**
  (initial commit, July 2026).
- Built with open-source software, under their licences: Django (BSD-3-Clause), PyJWT (MIT), google-genai (Apache-2.0),
  psycopg (LGPL-3.0), python-dotenv (BSD-3-Clause), cryptography (Apache-2.0/BSD), Pillow (MIT-CMU), redis-py (MIT),
  gunicorn (MIT), uuid6 (MIT); Vue, Vue Router, Pinia, vue-i18n, Vite, Tailwind CSS, axios (MIT), Tiptap (MIT),
  KaTeX (MIT), MathLive (MIT), Mermaid (MIT), three.js (MIT), Vue Flow (MIT), lowlight (MIT), OverlayScrollbars (MIT),
  splitpanes (MIT), qrcode-generator (MIT).
- Fonts: Plus Jakarta Sans, Geologica, Onest, Nunito, JetBrains Mono (SIL Open Font License 1.1).
- AI: Google Gemini API. Bank loan terms: the banks' public product pages (links in `backend/copilot/loans.py`).

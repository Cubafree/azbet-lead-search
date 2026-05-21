# AzBet Lead Search

Affiliate channel discovery tool for MENA region. Finds and qualifies Telegram channels, YouTube channels and affiliate websites using Google Search (Serper) + AI qualification (OpenAI).

## Stack

- **Backend**: Python + FastAPI
- **DB**: PostgreSQL (Railway)
- **AI**: OpenAI gpt-4.1-mini
- **Search**: Serper API (Google)
- **Frontend**: React + Vite + Tailwind

## Local setup

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in DATABASE_URL, OPENAI_API_KEY, SERPER_API_KEY

# Create tables
python -m db.migrations

# Start server
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # proxies /api → localhost:8000
```

## Usage

1. Open **Search Queries** tab — add queries like `site:t.me betting tips egypt`
2. Click **Run Search** — the pipeline runs in background:
   - Searches via Serper
   - Parses results by platform (TG / YouTube / web)
   - Enriches each channel (t.me scraping / yt-dlp / HTML)
   - AI qualifies with GPT-4.1-mini
3. View results in **Leads** tab — filter by platform, priority, geo, niche
4. Click any row to see contacts + AI summary

## Deploy to Railway

1. Connect repo to Railway
2. Add PostgreSQL service
3. Set env vars: `DATABASE_URL`, `OPENAI_API_KEY`, `SERPER_API_KEY`
4. Deploy — nixpacks builds frontend and backend together

## Cost estimate (per run)

| Leads processed | OpenAI cost |
|----------------|-------------|
| 500            | ~$0.13      |
| 2 000          | ~$0.50      |
| 10 000         | ~$2.50      |

# Company Enrichment Tool

AI-powered business intelligence pipeline that scrapes company websites and generates enriched profiles using GPT-4o-mini.

## Features

- **Smart Scraping**: Uses sitemap detection + fuzzy keyword matching to find relevant pages (About, Contact, Services)
- **Multi-approach scraping**: Fallback strategies for different website structures
- **Token Optimization**: HTML stripping, boilerplate removal, and chunking before AI processing
- **AI Enrichment**: GPT-4o-mini generates structured business profiles with anti-hallucination prompts
- **Web Interface**: Clean React UI with Enrich and Results sections
- **Loading States**: Visual progress indicators during enrichment

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend  │────▶│  Express API │────▶│   Scraper   │
│   (React)   │◀────│   (Node.js)  │◀────│  (Cheerio)  │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                      │
                           ▼                      ▼
                    ┌──────────────┐     ┌─────────────┐
                    │  JSON Store  │     │  OpenAI API │
                    └──────────────┘     └─────────────┘
```

## Quick Start

### Prerequisites
- Node.js 18+
- OpenAI API key

### Setup

```bash
# Install backend dependencies
npm install

# Install frontend dependencies and build
cd frontend && npm install && npx vite build && cd ..

# Set your API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Seed sample data (optional)
node seed-data.js

# Start the server
npm start
```

Visit http://localhost:3001

## API Endpoints

### POST /enrichInput
Enrich a single company URL.

**Request:**
```json
{
  "url": "https://www.example.com",
  "website_name": "Example Corp (optional)"
}
```

**Response:**
```json
{
  "website_name": "Example Corp",
  "company_name": "Example Corporation",
  "address": "123 Main St, City, State",
  "mobile_number": "+1-555-123-4567",
  "mail": ["info@example.com"],
  "core_service": "...",
  "target_customer": "...",
  "probable_pain_point": "...",
  "outreach_opener": "..."
}
```

### GET /results
Returns all enriched companies.

### POST /enrichBatch
Enrich multiple URLs at once.

**Request:**
```json
{
  "urls": ["https://www.stripe.com", "https://www.hubspot.com"]
}
```

## Deployment

### Render
1. Push to GitHub
2. Connect repo on Render
3. Set environment variable `OPENAI_API_KEY`
4. Deploy using `render.yaml`

### Docker
```bash
docker build -t company-enrichment .
docker run -p 3001:3001 -e OPENAI_API_KEY=your-key company-enrichment
```

## Google Colab

The standalone pipeline is in `colab_notebook.py`. Copy the cells into Google Colab:

1. Install dependencies: `!pip install beautifulsoup4 requests openai`
2. Set your API key
3. Run the pipeline cell — it prompts for a JSON array of URLs
4. Get structured JSON output + `results.json` file

## Scoring Approach

- **Scraping**: Sitemap-first, fuzzy keyword matching, multi-page with polite delays
- **Token Optimization**: HTML cleaning, boilerplate removal, truncation per page
- **Anti-hallucination**: Strict prompts requiring evidence from scraped content
- **Schema Stability**: Always returns valid JSON with N/A fallbacks
- **Error Handling**: Graceful degradation at every step

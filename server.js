require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');
const { scrapeCompany } = require('./scraper');
const { enrichCompany } = require('./enricher');
const { saveCompany, getAllCompanies, getCompanyByUrl } = require('./database');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Serve static frontend files
app.use(express.static(path.join(__dirname, 'frontend', 'dist')));

/**
 * POST /enrichInput
 * Takes a company URL and returns enriched company profile
 */
app.post('/enrichInput', async (req, res) => {
  try {
    const { url, website_name } = req.body;

    if (!url) {
      return res.status(400).json({ error: 'URL is required' });
    }

    // Normalize URL
    let normalizedUrl = url.trim();
    if (!normalizedUrl.startsWith('http')) {
      normalizedUrl = 'https://' + normalizedUrl;
    }

    console.log(`[API] Enriching: ${normalizedUrl}`);

    // Step 1: Scrape the website
    const scrapedData = await scrapeCompany(normalizedUrl);

    if (scrapedData.error) {
      return res.status(422).json({ error: scrapedData.error });
    }

    // Step 2: Enrich with AI
    const enrichedProfile = await enrichCompany(scrapedData, normalizedUrl);

    // Override website_name if provided by user
    if (website_name && website_name.trim()) {
      enrichedProfile.website_name = website_name.trim();
    }

    // Step 3: Save to database
    saveCompany(normalizedUrl, enrichedProfile);

    console.log(`[API] Successfully enriched: ${enrichedProfile.company_name}`);
    res.json(enrichedProfile);
  } catch (err) {
    console.error(`[API] Error enriching:`, err.message);
    res.status(500).json({ error: 'Internal server error during enrichment' });
  }
});

/**
 * GET /results
 * Returns all enriched companies
 */
app.get('/results', (req, res) => {
  try {
    const companies = getAllCompanies();
    res.json(companies);
  } catch (err) {
    console.error(`[API] Error fetching results:`, err.message);
    res.status(500).json({ error: 'Failed to fetch results' });
  }
});

/**
 * POST /enrichBatch
 * Takes an array of URLs and returns enriched profiles for all
 */
app.post('/enrichBatch', async (req, res) => {
  try {
    const { urls } = req.body;

    if (!urls || !Array.isArray(urls) || urls.length === 0) {
      return res.status(400).json({ error: 'Array of URLs is required' });
    }

    const results = [];
    for (const url of urls) {
      let normalizedUrl = url.trim();
      if (!normalizedUrl.startsWith('http')) {
        normalizedUrl = 'https://' + normalizedUrl;
      }

      console.log(`[API Batch] Enriching: ${normalizedUrl}`);
      const scrapedData = await scrapeCompany(normalizedUrl);

      if (scrapedData.error) {
        results.push({
          website_name: 'N/A',
          company_name: 'N/A',
          address: 'N/A',
          mobile_number: 'N/A',
          mail: [],
          core_service: 'N/A',
          target_customer: 'N/A',
          probable_pain_point: 'N/A',
          outreach_opener: 'N/A',
        });
        continue;
      }

      const enrichedProfile = await enrichCompany(scrapedData, normalizedUrl);
      saveCompany(normalizedUrl, enrichedProfile);
      results.push(enrichedProfile);
    }

    res.json(results);
  } catch (err) {
    console.error(`[API Batch] Error:`, err.message);
    res.status(500).json({ error: 'Internal server error during batch enrichment' });
  }
});

// Catch-all: serve frontend for any non-API route
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'frontend', 'dist', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`[Server] Company Enrichment API running on port ${PORT}`);
  console.log(`[Server] Frontend: http://localhost:${PORT}`);
  console.log(`[Server] API: http://localhost:${PORT}/enrichInput (POST)`);
  console.log(`[Server] API: http://localhost:${PORT}/results (GET)`);
});

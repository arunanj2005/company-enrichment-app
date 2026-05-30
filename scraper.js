const axios = require('axios');
const cheerio = require('cheerio');
const robotsParser = require('robots-parser');

// Fuzzy matching keywords for relevant pages
const RELEVANT_PAGE_KEYWORDS = [
  'about', 'contact', 'services', 'solutions', 'team', 'company',
  'what-we-do', 'our-work', 'industries', 'clients', 'partners',
  'products', 'offerings', 'capabilities', 'who-we-are', 'mission',
  'overview', 'pricing', 'plans'
];

const IRRELEVANT_KEYWORDS = [
  'blog', 'news', 'press', 'careers', 'jobs', 'login', 'signup',
  'register', 'cart', 'checkout', 'privacy', 'terms', 'cookie',
  'sitemap.xml', 'feed', 'rss', 'wp-admin', 'wp-content',
  'cdn', 'assets', 'static', 'media', '#', 'javascript:', 'mailto:'
];

const USER_AGENTS = [
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
];

function getRandomUserAgent() {
  return USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Normalize a URL relative to a base
 */
function normalizeUrl(href, baseUrl) {
  try {
    if (!href || href.startsWith('#') || href.startsWith('javascript:') || href.startsWith('mailto:')) {
      return null;
    }
    const url = new URL(href, baseUrl);
    // Only keep same-domain links
    const base = new URL(baseUrl);
    if (url.hostname !== base.hostname) return null;
    // Remove fragments and trailing slashes
    url.hash = '';
    let normalized = url.toString();
    if (normalized.endsWith('/') && normalized !== baseUrl + '/') {
      normalized = normalized.slice(0, -1);
    }
    return normalized;
  } catch {
    return null;
  }
}

/**
 * Score a URL for relevance based on fuzzy keyword matching
 */
function scoreUrl(url) {
  const lower = url.toLowerCase();
  // Check if it matches irrelevant patterns
  for (const kw of IRRELEVANT_KEYWORDS) {
    if (lower.includes(kw)) return -1;
  }
  // Score based on relevant keywords
  let score = 0;
  for (const kw of RELEVANT_PAGE_KEYWORDS) {
    if (lower.includes(kw)) score += 2;
  }
  // Prefer shorter paths (closer to root)
  const pathDepth = (new URL(url).pathname.match(/\//g) || []).length;
  score -= pathDepth * 0.5;
  return score;
}

/**
 * Fetch a page with retries and proper headers
 */
async function fetchPage(url, retries = 2) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await axios.get(url, {
        headers: {
          'User-Agent': getRandomUserAgent(),
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.9',
          'Accept-Encoding': 'gzip, deflate',
          'Connection': 'keep-alive',
        },
        timeout: 15000,
        maxRedirects: 5,
        validateStatus: (status) => status < 400,
      });
      return response.data;
    } catch (err) {
      if (attempt === retries) {
        console.error(`Failed to fetch ${url}: ${err.message}`);
        return null;
      }
      await delay(1000 * (attempt + 1));
    }
  }
  return null;
}

/**
 * Try to fetch and parse sitemap.xml for relevant URLs
 */
async function fetchSitemap(baseUrl) {
  const sitemapUrls = [
    `${baseUrl}/sitemap.xml`,
    `${baseUrl}/sitemap_index.xml`,
    `${baseUrl}/sitemap/sitemap.xml`
  ];

  for (const sitemapUrl of sitemapUrls) {
    try {
      const data = await fetchPage(sitemapUrl);
      if (!data) continue;
      const $ = cheerio.load(data, { xmlMode: true });
      const urls = [];
      $('url > loc').each((_, el) => {
        urls.push($(el).text().trim());
      });
      if (urls.length > 0) return urls;
    } catch {
      continue;
    }
  }
  return [];
}

/**
 * Extract links from a page's HTML
 */
function extractLinks(html, baseUrl) {
  const $ = cheerio.load(html);
  const links = new Set();
  $('a[href]').each((_, el) => {
    const href = $(el).attr('href');
    const normalized = normalizeUrl(href, baseUrl);
    if (normalized) links.add(normalized);
  });
  return Array.from(links);
}

/**
 * Clean HTML content - remove boilerplate, scripts, styles, nav, footer
 */
function cleanHtml(html) {
  const $ = cheerio.load(html);

  // Remove non-content elements
  $('script, style, noscript, iframe, svg, img, video, audio').remove();
  $('nav, header, footer, .nav, .navbar, .header, .footer').remove();
  $('.cookie, .cookies, .cookie-banner, .cookie-consent').remove();
  $('[class*="cookie"], [id*="cookie"]').remove();
  $('[class*="popup"], [id*="popup"], [class*="modal"], [id*="modal"]').remove();
  $('[class*="sidebar"], [id*="sidebar"]').remove();
  $('[class*="menu"], [id*="menu"]').remove();
  $('[class*="social"], [id*="social"]').remove();
  $('[class*="share"], [id*="share"]').remove();
  $('[class*="newsletter"], [id*="newsletter"]').remove();
  $('[class*="subscribe"], [id*="subscribe"]').remove();
  $('[class*="ad-"], [id*="ad-"], .advertisement').remove();

  // Get text content from main content areas
  let text = '';
  
  // Try to find main content area first
  const mainSelectors = ['main', 'article', '[role="main"]', '.content', '.main-content', '#content', '#main'];
  for (const selector of mainSelectors) {
    const mainContent = $(selector).text();
    if (mainContent && mainContent.trim().length > 100) {
      text = mainContent;
      break;
    }
  }

  // Fallback to body text
  if (!text || text.trim().length < 100) {
    text = $('body').text();
  }

  // Clean up whitespace
  text = text
    .replace(/\s+/g, ' ')
    .replace(/\n\s*\n/g, '\n')
    .trim();

  return text;
}

/**
 * Extract structured data (emails, phones, addresses) from HTML
 */
function extractContactInfo(html) {
  const $ = cheerio.load(html);
  const fullText = $('body').text();

  // Extract emails
  const emailRegex = /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g;
  const emails = [...new Set((fullText.match(emailRegex) || [])
    .filter(e => !e.includes('example.com') && !e.includes('sentry') && !e.includes('webpack'))
  )];

  // Extract phone numbers
  const phoneRegex = /(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}/g;
  const phones = [...new Set((fullText.match(phoneRegex) || [])
    .map(p => p.trim())
    .filter(p => p.replace(/\D/g, '').length >= 10)
  )];

  // Try to extract from structured elements
  const structuredEmails = [];
  $('a[href^="mailto:"]').each((_, el) => {
    const email = $(el).attr('href').replace('mailto:', '').split('?')[0].trim();
    if (email && !structuredEmails.includes(email)) structuredEmails.push(email);
  });

  const structuredPhones = [];
  $('a[href^="tel:"]').each((_, el) => {
    const phone = $(el).attr('href').replace('tel:', '').trim();
    if (phone) structuredPhones.push(phone);
  });

  // Merge structured and regex-found data
  const allEmails = [...new Set([...structuredEmails, ...emails])];
  const allPhones = [...new Set([...structuredPhones, ...phones])];

  return { emails: allEmails, phones: allPhones };
}

/**
 * Extract meta information from HTML
 */
function extractMeta(html) {
  const $ = cheerio.load(html);
  return {
    title: $('title').text().trim() || $('meta[property="og:title"]').attr('content') || '',
    description: $('meta[name="description"]').attr('content') || $('meta[property="og:description"]').attr('content') || '',
    siteName: $('meta[property="og:site_name"]').attr('content') || '',
  };
}

/**
 * Main scraping function - orchestrates the multi-page scraping
 */
async function scrapeCompany(url) {
  console.log(`[Scraper] Starting scrape for: ${url}`);
  
  // Normalize base URL
  let baseUrl = url.trim();
  if (!baseUrl.startsWith('http')) baseUrl = 'https://' + baseUrl;
  if (baseUrl.endsWith('/')) baseUrl = baseUrl.slice(0, -1);

  // Step 1: Fetch homepage
  const homepageHtml = await fetchPage(baseUrl);
  if (!homepageHtml) {
    // Fallback: try with www
    const withWww = baseUrl.replace('https://', 'https://www.');
    const fallbackHtml = await fetchPage(withWww);
    if (!fallbackHtml) {
      return { error: `Could not fetch ${url}`, rawTexts: [], contactInfo: { emails: [], phones: [] }, meta: {} };
    }
    return processScrapedData(fallbackHtml, withWww);
  }

  return processScrapedData(homepageHtml, baseUrl);
}

async function processScrapedData(homepageHtml, baseUrl) {
  // Extract meta and contact info from homepage
  const meta = extractMeta(homepageHtml);
  const homepageContact = extractContactInfo(homepageHtml);
  const homepageText = cleanHtml(homepageHtml);

  // Step 2: Find relevant pages via sitemap or link extraction
  let candidateUrls = [];
  
  // Try sitemap first
  const sitemapUrls = await fetchSitemap(baseUrl);
  if (sitemapUrls.length > 0) {
    candidateUrls = sitemapUrls;
    console.log(`[Scraper] Found ${sitemapUrls.length} URLs from sitemap`);
  } else {
    // Extract links from homepage
    candidateUrls = extractLinks(homepageHtml, baseUrl);
    console.log(`[Scraper] Found ${candidateUrls.length} links from homepage`);
  }

  // Step 3: Score and select top relevant pages
  const scoredUrls = candidateUrls
    .map(u => ({ url: u, score: scoreUrl(u) }))
    .filter(u => u.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5); // Max 5 additional pages

  console.log(`[Scraper] Selected ${scoredUrls.length} relevant pages to scrape`);

  // Step 4: Scrape relevant pages with delays
  const allTexts = [homepageText];
  const allContacts = { emails: [...homepageContact.emails], phones: [...homepageContact.phones] };

  for (const { url: pageUrl } of scoredUrls) {
    await delay(500); // Polite delay
    const pageHtml = await fetchPage(pageUrl);
    if (pageHtml) {
      const pageText = cleanHtml(pageHtml);
      if (pageText.length > 50) {
        allTexts.push(pageText);
      }
      const pageContact = extractContactInfo(pageHtml);
      allContacts.emails.push(...pageContact.emails);
      allContacts.phones.push(...pageContact.phones);
    }
  }

  // Deduplicate contacts
  allContacts.emails = [...new Set(allContacts.emails)];
  allContacts.phones = [...new Set(allContacts.phones)];

  return {
    rawTexts: allTexts,
    contactInfo: allContacts,
    meta,
    baseUrl,
  };
}

module.exports = { scrapeCompany, cleanHtml, extractContactInfo, extractMeta };

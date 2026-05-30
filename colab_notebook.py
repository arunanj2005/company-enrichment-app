"""
Company Enrichment Pipeline - Google Colab Notebook
====================================================
This script is designed to run in Google Colab.
It takes an array of company URLs as input and outputs enriched JSON profiles.

Instructions:
1. Run the cell to install dependencies
2. Run the main cell - it will prompt you for URLs
3. Paste your JSON array of URLs
4. Get the enriched JSON output

Dependencies cell:
!pip install beautifulsoup4 requests openai

"""

# ============================================================
# CELL 1: Install Dependencies
# ============================================================
# !pip install beautifulsoup4 requests openai lxml

# ============================================================
# CELL 2: Imports and Configuration
# ============================================================
import json
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from openai import OpenAI

# ============================================================
# CELL 3: Set your API Key
# ============================================================
import os

# OpenRouter API Key - uses Colab secrets or prompts for input
OPENROUTER_API_KEY = None

try:
    from google.colab import userdata
    OPENROUTER_API_KEY = userdata.get('OPENROUTER_API_KEY')
except:
    pass

if not OPENROUTER_API_KEY:
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

if not OPENROUTER_API_KEY:
    OPENROUTER_API_KEY = input("Enter your OpenRouter API Key: ")

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)
print("✓ AI client initialized (OpenRouter)")

# ============================================================
# CELL 4: Scraping Functions
# ============================================================

RELEVANT_PAGE_KEYWORDS = [
    'about', 'contact', 'services', 'solutions', 'team', 'company',
    'what-we-do', 'our-work', 'industries', 'clients', 'partners',
    'products', 'offerings', 'capabilities', 'who-we-are', 'mission',
    'overview', 'pricing', 'plans'
]

IRRELEVANT_KEYWORDS = [
    'blog', 'news', 'press', 'careers', 'jobs', 'login', 'signup',
    'register', 'cart', 'checkout', 'privacy', 'terms', 'cookie',
    'sitemap.xml', 'feed', 'rss', 'wp-admin', 'wp-content',
    'cdn', 'assets', 'static', 'media', '#', 'javascript:', 'mailto:'
]

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

def get_headers():
    """Get request headers with rotating user agent"""
    import random
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
    }

def fetch_page(url, retries=2):
    """Fetch a page with retries"""
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=get_headers(), timeout=15, allow_redirects=True)
            if response.status_code < 400:
                return response.text
        except Exception as e:
            if attempt == retries:
                print(f"  [!] Failed to fetch {url}: {e}")
                return None
            time.sleep(1 * (attempt + 1))
    return None

def normalize_url(href, base_url):
    """Normalize a URL relative to base"""
    if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
        return None
    try:
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        base_parsed = urlparse(base_url)
        if parsed.hostname != base_parsed.hostname:
            return None
        # Remove fragment
        clean = parsed._replace(fragment='').geturl()
        return clean.rstrip('/')
    except:
        return None

def score_url(url):
    """Score URL for relevance using fuzzy keyword matching"""
    lower = url.lower()
    for kw in IRRELEVANT_KEYWORDS:
        if kw in lower:
            return -1
    score = 0
    for kw in RELEVANT_PAGE_KEYWORDS:
        if kw in lower:
            score += 2
    # Prefer shorter paths
    path_depth = urlparse(url).path.count('/')
    score -= path_depth * 0.5
    return score

def fetch_sitemap(base_url):
    """Try to fetch sitemap for relevant URLs"""
    sitemap_urls = [
        f"{base_url}/sitemap.xml",
        f"{base_url}/sitemap_index.xml",
    ]
    for sitemap_url in sitemap_urls:
        try:
            html = fetch_page(sitemap_url)
            if not html:
                continue
            soup = BeautifulSoup(html, 'xml')
            urls = [loc.text.strip() for loc in soup.find_all('loc')]
            if urls:
                return urls
        except:
            continue
    return []

def extract_links(html, base_url):
    """Extract all same-domain links from HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    links = set()
    for a in soup.find_all('a', href=True):
        normalized = normalize_url(a['href'], base_url)
        if normalized:
            links.add(normalized)
    return list(links)

def clean_html(html):
    """Remove boilerplate and extract meaningful text"""
    soup = BeautifulSoup(html, 'html.parser')

    # Remove non-content elements
    for tag in soup.find_all(['script', 'style', 'noscript', 'iframe', 'svg', 'img', 'video', 'audio']):
        tag.decompose()
    for tag in soup.find_all(['nav', 'header', 'footer']):
        tag.decompose()

    # Remove by class/id patterns
    for pattern in ['cookie', 'popup', 'modal', 'sidebar', 'menu', 'social', 'share', 'newsletter', 'subscribe', 'ad-']:
        for tag in soup.find_all(attrs={'class': re.compile(pattern, re.I)}):
            tag.decompose()
        for tag in soup.find_all(attrs={'id': re.compile(pattern, re.I)}):
            tag.decompose()

    # Try main content area first
    main_selectors = ['main', 'article', '[role="main"]', '.content', '.main-content', '#content', '#main']
    text = ''
    for selector in main_selectors:
        main = soup.select_one(selector)
        if main and len(main.get_text(strip=True)) > 100:
            text = main.get_text(separator=' ', strip=True)
            break

    if not text or len(text) < 100:
        text = soup.get_text(separator=' ', strip=True)

    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_contact_info(html):
    """Extract emails and phone numbers from HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    full_text = soup.get_text()

    # Emails
    email_regex = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    emails = list(set(re.findall(email_regex, full_text)))
    emails = [e for e in emails if 'example.com' not in e and 'sentry' not in e and 'webpack' not in e]

    # Structured emails from mailto links
    for a in soup.find_all('a', href=re.compile(r'^mailto:')):
        email = a['href'].replace('mailto:', '').split('?')[0].strip()
        if email and email not in emails:
            emails.insert(0, email)

    # Phone numbers
    phone_regex = r'(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
    phones = list(set(re.findall(phone_regex, full_text)))
    phones = [p.strip() for p in phones if len(re.sub(r'\D', '', p)) >= 10]

    # Structured phones from tel links
    for a in soup.find_all('a', href=re.compile(r'^tel:')):
        phone = a['href'].replace('tel:', '').strip()
        if phone and phone not in phones:
            phones.insert(0, phone)

    return {'emails': emails, 'phones': phones}

def extract_meta(html):
    """Extract meta information"""
    soup = BeautifulSoup(html, 'html.parser')
    title = ''
    if soup.title:
        title = soup.title.string or ''
    og_title = soup.find('meta', attrs={'property': 'og:title'})
    if not title and og_title:
        title = og_title.get('content', '')

    desc_tag = soup.find('meta', attrs={'name': 'description'})
    og_desc = soup.find('meta', attrs={'property': 'og:description'})
    description = ''
    if desc_tag:
        description = desc_tag.get('content', '')
    elif og_desc:
        description = og_desc.get('content', '')

    site_name_tag = soup.find('meta', attrs={'property': 'og:site_name'})
    site_name = site_name_tag.get('content', '') if site_name_tag else ''

    return {'title': title.strip(), 'description': description.strip(), 'site_name': site_name.strip()}

def scrape_company(url):
    """Main scraping orchestrator"""
    print(f"  [*] Scraping: {url}")

    # Normalize URL
    base_url = url.strip()
    if not base_url.startswith('http'):
        base_url = 'https://' + base_url
    base_url = base_url.rstrip('/')

    # Fetch homepage
    homepage_html = fetch_page(base_url)
    if not homepage_html:
        # Try with www
        alt_url = base_url.replace('https://', 'https://www.')
        homepage_html = fetch_page(alt_url)
        if not homepage_html:
            return {'error': f'Could not fetch {url}', 'raw_texts': [], 'contact_info': {'emails': [], 'phones': []}, 'meta': {}}
        base_url = alt_url

    # Extract meta and contacts from homepage
    meta = extract_meta(homepage_html)
    homepage_contact = extract_contact_info(homepage_html)
    homepage_text = clean_html(homepage_html)

    # Find relevant pages
    candidate_urls = []
    sitemap_urls = fetch_sitemap(base_url)
    if sitemap_urls:
        candidate_urls = sitemap_urls
        print(f"  [*] Found {len(sitemap_urls)} URLs from sitemap")
    else:
        candidate_urls = extract_links(homepage_html, base_url)
        print(f"  [*] Found {len(candidate_urls)} links from homepage")

    # Score and select top relevant pages
    scored = [(u, score_url(u)) for u in candidate_urls]
    scored = [(u, s) for u, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    top_pages = scored[:5]

    print(f"  [*] Selected {len(top_pages)} relevant pages")

    # Scrape relevant pages
    all_texts = [homepage_text]
    all_contacts = {'emails': list(homepage_contact['emails']), 'phones': list(homepage_contact['phones'])}

    for page_url, _ in top_pages:
        time.sleep(0.5)
        page_html = fetch_page(page_url)
        if page_html:
            page_text = clean_html(page_html)
            if len(page_text) > 50:
                all_texts.append(page_text)
            page_contact = extract_contact_info(page_html)
            all_contacts['emails'].extend(page_contact['emails'])
            all_contacts['phones'].extend(page_contact['phones'])

    # Deduplicate
    all_contacts['emails'] = list(set(all_contacts['emails']))
    all_contacts['phones'] = list(set(all_contacts['phones']))

    return {
        'raw_texts': all_texts,
        'contact_info': all_contacts,
        'meta': meta,
        'base_url': base_url,
    }

# ============================================================
# CELL 5: AI Enrichment Functions
# ============================================================

def truncate_for_tokens(text, max_tokens=3000):
    """Truncate text to fit token budget (1 token ≈ 4 chars)"""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + '\n[...truncated]'

def prepare_context(scraped_data):
    """Prepare scraped data for LLM"""
    raw_texts = scraped_data['raw_texts']
    contact_info = scraped_data['contact_info']
    meta = scraped_data['meta']

    combined = '\n\n'.join([
        f"--- Page {i+1} ---\n{truncate_for_tokens(t, 1500)}"
        for i, t in enumerate(raw_texts)
    ])

    context = ''
    if meta.get('title'):
        context += f"Website Title: {meta['title']}\n"
    if meta.get('description'):
        context += f"Meta Description: {meta['description']}\n"
    if meta.get('site_name'):
        context += f"Site Name: {meta['site_name']}\n"
    if contact_info['emails']:
        context += f"Found Emails: {', '.join(contact_info['emails'])}\n"
    if contact_info['phones']:
        context += f"Found Phones: {', '.join(contact_info['phones'])}\n"
    context += f"\n--- Scraped Content ---\n{combined}"

    return truncate_for_tokens(context, 6000)

def enrich_company(scraped_data, website_url):
    """Use AI to generate enriched company profile"""
    context = prepare_context(scraped_data)

    system_prompt = """You are a business intelligence analyst. Your job is to extract and infer company information from scraped website data.

CRITICAL RULES:
1. ONLY use information that is explicitly present or can be reasonably inferred from the provided content.
2. If information is NOT found in the content, return "N/A" for that field - NEVER fabricate or hallucinate data.
3. For emails and phone numbers, ONLY include those actually found in the scraped content.
4. For "core_service", summarize what the company actually does based on the content.
5. For "target_customer", infer from the content who their services are aimed at.
6. For "probable_pain_point", infer a realistic business challenge their customers face.
7. For "outreach_opener", write a personalized, professional cold outreach message (1-2 sentences).

Return ONLY valid JSON matching this exact schema:
{
  "website_name": "string - the website/brand name",
  "company_name": "string - full legal/official company name if found, otherwise brand name",
  "address": "string - physical address if found, otherwise N/A",
  "mobile_number": "string - primary phone number if found, otherwise N/A",
  "mail": ["array of email addresses found, empty array if none"],
  "core_service": "string - main service/product offering",
  "target_customer": "string - who their ideal customers are",
  "probable_pain_point": "string - likely pain point of their target customers",
  "outreach_opener": "string - personalized cold outreach opener"
}"""

    user_prompt = f"""Analyze this company website data and extract a business profile.

Website URL: {website_url}

{context}

Return ONLY the JSON object, no markdown formatting, no code blocks."""

    try:
        response = client.chat.completions.create(
            model='openai/gpt-4o-mini',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            temperature=0.3,
            max_tokens=800,
        )

        content = response.choices[0].message.content
        # Handle potential markdown wrapping
        json_str = content.strip()
        if json_str.startswith('```'):
            json_str = re.sub(r'^```(?:json)?\n?', '', json_str)
            json_str = re.sub(r'\n?```$', '', json_str)
        parsed = json.loads(json_str)

        # Ensure schema compliance
        return {
            'website_name': parsed.get('website_name', 'N/A'),
            'company_name': parsed.get('company_name', 'N/A'),
            'address': parsed.get('address', 'N/A'),
            'mobile_number': parsed.get('mobile_number', 'N/A'),
            'mail': parsed.get('mail', []) if isinstance(parsed.get('mail'), list) else [],
            'core_service': parsed.get('core_service', 'N/A'),
            'target_customer': parsed.get('target_customer', 'N/A'),
            'probable_pain_point': parsed.get('probable_pain_point', 'N/A'),
            'outreach_opener': parsed.get('outreach_opener', 'N/A'),
        }
    except Exception as e:
        print(f"  [!] AI enrichment failed: {e}")
        meta = scraped_data.get('meta', {})
        contact = scraped_data.get('contact_info', {})
        return {
            'website_name': meta.get('title', 'N/A'),
            'company_name': meta.get('site_name', 'N/A'),
            'address': 'N/A',
            'mobile_number': contact.get('phones', ['N/A'])[0] if contact.get('phones') else 'N/A',
            'mail': contact.get('emails', []),
            'core_service': meta.get('description', 'N/A'),
            'target_customer': 'N/A',
            'probable_pain_point': 'N/A',
            'outreach_opener': 'N/A',
        }

# ============================================================
# CELL 6: Main Pipeline - Run this cell
# ============================================================

def run_pipeline():
    """Main pipeline function - prompts for URLs and outputs enriched JSON"""
    print("=" * 60)
    print("  COMPANY ENRICHMENT PIPELINE")
    print("=" * 60)
    print()
    print("Enter a JSON array of company URLs.")
    print('Example: ["https://www.stripe.com", "https://www.hubspot.com"]')
    print()

    # Get input from user
    url_input = input("Paste your URL array here: ")

    # Parse input
    try:
        urls = json.loads(url_input)
        if not isinstance(urls, list):
            urls = [urls]
    except json.JSONDecodeError:
        # Try to handle comma-separated or single URL
        urls = [u.strip().strip('"').strip("'") for u in url_input.split(',')]

    print(f"\n[*] Processing {len(urls)} URLs...\n")

    results = []
    for i, url in enumerate(urls):
        print(f"\n{'='*40}")
        print(f"  Processing [{i+1}/{len(urls)}]: {url}")
        print(f"{'='*40}")

        # Scrape
        scraped_data = scrape_company(url)

        if scraped_data.get('error'):
            print(f"  [!] Error: {scraped_data['error']}")
            results.append({
                'website_name': 'N/A',
                'company_name': 'N/A',
                'address': 'N/A',
                'mobile_number': 'N/A',
                'mail': [],
                'core_service': 'N/A',
                'target_customer': 'N/A',
                'probable_pain_point': 'N/A',
                'outreach_opener': 'N/A',
            })
            continue

        # Enrich
        print(f"  [*] Enriching with AI...")
        enriched = enrich_company(scraped_data, url)
        results.append(enriched)
        print(f"  [✓] Done: {enriched['company_name']}")

    # Output results
    print("\n\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print()
    output = json.dumps(results, indent=2, ensure_ascii=False)
    print(output)

    # Save to file
    with open('results.json', 'w') as f:
        f.write(output)
    print("\n[✓] Results saved to results.json")

    return results

# Run the pipeline
results = run_pipeline()

# ================================
# 🏆 Hackathon Template Notebook
# Prospect Research Agent
# ================================

# ========= INSTALL DEPENDENCIES =========
# !pip install beautifulsoup4 requests openai lxml

# ========= IMPORTS =========
import json
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from openai import OpenAI

# ========= CONFIG =========
# 🔑 Add your API key here
API_KEY = "YOUR_OPENROUTER_API_KEY"  # Replace with your OpenRouter API key

# Initialize AI client (OpenRouter - OpenAI compatible)
client = OpenAI(
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

# ========= SCRAPING HELPERS =========

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
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
    }


def fetch_page(url, retries=2):
    """Fetch a page with retries and polite delays"""
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=get_headers(), timeout=15, allow_redirects=True)
            if response.status_code < 400:
                return response.text
        except Exception as e:
            if attempt == retries:
                print(f"    [!] Failed to fetch {url}: {e}")
                return None
            time.sleep(1 * (attempt + 1))
    return None


def normalize_url(href, base_url):
    """Normalize a URL relative to base, keep same-domain only"""
    if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
        return None
    try:
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        base_parsed = urlparse(base_url)
        if parsed.hostname != base_parsed.hostname:
            return None
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
    path_depth = urlparse(url).path.count('/')
    score -= path_depth * 0.5
    return score


def fetch_sitemap(base_url):
    """Try to fetch sitemap.xml for relevant URLs"""
    sitemap_urls = [f"{base_url}/sitemap.xml", f"{base_url}/sitemap_index.xml"]
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
    """Remove boilerplate (nav, footer, scripts, ads) and extract meaningful text"""
    soup = BeautifulSoup(html, 'html.parser')

    # Remove non-content elements
    for tag in soup.find_all(['script', 'style', 'noscript', 'iframe', 'svg', 'img', 'video', 'audio']):
        tag.decompose()
    for tag in soup.find_all(['nav', 'header', 'footer']):
        tag.decompose()

    # Remove by class/id patterns (cookie banners, popups, sidebars, ads)
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

    # Emails via regex
    email_regex = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    emails = list(set(re.findall(email_regex, full_text)))
    emails = [e for e in emails if 'example.com' not in e and 'sentry' not in e and 'webpack' not in e and 'wixpress' not in e]

    # Structured emails from mailto links
    for a in soup.find_all('a', href=re.compile(r'^mailto:')):
        email = a['href'].replace('mailto:', '').split('?')[0].strip()
        if email and email not in emails:
            emails.insert(0, email)

    # Phone numbers via regex
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
    """Extract meta title, description, site name"""
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


def scrape_website(url):
    """
    Main scraping orchestrator:
    1. Fetch homepage
    2. Try sitemap or extract links
    3. Score links with fuzzy matching
    4. Scrape top 5 relevant pages
    5. Return cleaned text + contact info
    """
    print(f"    [*] Scraping: {url}")

    # Normalize URL
    base_url = url.strip()
    if not base_url.startswith('http'):
        base_url = 'https://' + base_url
    base_url = base_url.rstrip('/')

    # Fetch homepage
    homepage_html = fetch_page(base_url)
    if not homepage_html:
        # Fallback: try with www
        alt_url = base_url.replace('https://', 'https://www.')
        homepage_html = fetch_page(alt_url)
        if not homepage_html:
            return None
        base_url = alt_url

    # Extract meta and contacts from homepage
    meta = extract_meta(homepage_html)
    homepage_contact = extract_contact_info(homepage_html)
    homepage_text = clean_html(homepage_html)

    # Find relevant pages via sitemap or link extraction
    candidate_urls = []
    sitemap_urls = fetch_sitemap(base_url)
    if sitemap_urls:
        candidate_urls = sitemap_urls
        print(f"    [*] Found {len(sitemap_urls)} URLs from sitemap")
    else:
        candidate_urls = extract_links(homepage_html, base_url)
        print(f"    [*] Found {len(candidate_urls)} links from homepage")

    # Score and select top relevant pages
    scored = [(u, score_url(u)) for u in candidate_urls]
    scored = [(u, s) for u, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    top_pages = scored[:5]

    print(f"    [*] Selected {len(top_pages)} relevant pages to scrape")

    # Scrape relevant pages with polite delays
    all_texts = [homepage_text]
    all_contacts = {'emails': list(homepage_contact['emails']), 'phones': list(homepage_contact['phones'])}

    for page_url, _ in top_pages:
        time.sleep(0.5)  # Polite delay
        page_html = fetch_page(page_url)
        if page_html:
            page_text = clean_html(page_html)
            if len(page_text) > 50:
                all_texts.append(page_text)
            page_contact = extract_contact_info(page_html)
            all_contacts['emails'].extend(page_contact['emails'])
            all_contacts['phones'].extend(page_contact['phones'])

    # Deduplicate contacts
    all_contacts['emails'] = list(set(all_contacts['emails']))
    all_contacts['phones'] = list(set(all_contacts['phones']))

    return {
        'raw_texts': all_texts,
        'contact_info': all_contacts,
        'meta': meta,
        'base_url': base_url,
    }


# ========= TOKEN OPTIMIZATION =========

def truncate_for_tokens(text, max_tokens=3000):
    """Truncate text to fit token budget (1 token ≈ 4 chars)"""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + '\n[...truncated]'


def prepare_context(scraped_data):
    """Prepare scraped data for LLM - heavy optimization to reduce tokens"""
    raw_texts = scraped_data['raw_texts']
    contact_info = scraped_data['contact_info']
    meta = scraped_data['meta']

    # Combine texts, truncate each page individually
    combined = '\n\n'.join([
        f"--- Page {i+1} ---\n{truncate_for_tokens(t, 1500)}"
        for i, t in enumerate(raw_texts)
    ])

    # Build structured context
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

    # Final truncation to stay within total budget
    return truncate_for_tokens(context, 6000)


# ========= AI ENRICHMENT =========

def ai_enrich(scraped_data, website_url):
    """Use AI (GPT-4o-mini via OpenRouter) to generate structured company profile"""
    context = prepare_context(scraped_data)

    system_prompt = """You are a business intelligence analyst. Extract and infer company information from scraped website data.

CRITICAL RULES:
1. ONLY use information explicitly present or reasonably inferred from the provided content.
2. If information is NOT found, return "N/A" for that field - NEVER fabricate or hallucinate data.
3. For emails and phone numbers, ONLY include those actually found in the scraped content.
4. For "core_service", summarize what the company actually does based on the content.
5. For "target_customer", infer from the content who their services are aimed at.
6. For "probable_pain_point", infer a realistic business challenge their customers face.
7. For "outreach_opener", write a personalized, professional cold outreach message (1-2 sentences).

Return ONLY valid JSON matching this exact schema:
{
  "website_name": "string",
  "company_name": "string",
  "address": "string or N/A",
  "mobile_number": "string or N/A",
  "mail": ["array of emails found, empty array if none"],
  "core_service": "string",
  "target_customer": "string",
  "probable_pain_point": "string",
  "outreach_opener": "string"
}"""

    user_prompt = f"""Analyze this company website data and extract a business profile.

Website URL: {website_url}

{context}

Return ONLY the JSON object, no markdown, no code blocks."""

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
        print(f"    [!] AI enrichment failed: {e}")
        # Fallback: return what we scraped without AI
        meta = scraped_data.get('meta', {})
        contact = scraped_data.get('contact_info', {})
        return {
            'website_name': meta.get('title', 'N/A'),
            'company_name': meta.get('site_name', meta.get('title', 'N/A')),
            'address': 'N/A',
            'mobile_number': contact.get('phones', ['N/A'])[0] if contact.get('phones') else 'N/A',
            'mail': contact.get('emails', []),
            'core_service': meta.get('description', 'N/A'),
            'target_customer': 'N/A',
            'probable_pain_point': 'N/A',
            'outreach_opener': 'N/A',
        }


# ========= REQUIRED FUNCTION =========

def enrich_company(url: str) -> dict:
    """
    Input: Company URL
    Output: Structured company profile (STRICT FORMAT)

    Pipeline:
    1. Smart scrape (sitemap + fuzzy matching for relevant pages)
    2. Clean HTML (remove boilerplate, optimize tokens)
    3. AI enrichment (GPT-4o-mini via OpenRouter)
    4. Return structured JSON
    """
    print(f"\n  Processing: {url}")
    print(f"  {'─' * 40}")

    # Step 1: Scrape the website
    scraped_data = scrape_website(url)

    if scraped_data is None:
        print(f"    [!] Could not fetch website")
        return {
            'website_name': 'N/A',
            'company_name': 'N/A',
            'address': 'N/A',
            'mobile_number': 'N/A',
            'mail': [],
            'core_service': 'N/A',
            'target_customer': 'N/A',
            'probable_pain_point': 'N/A',
            'outreach_opener': 'N/A',
        }

    # Step 2: AI Enrichment
    print(f"    [*] Enriching with AI...")
    result = ai_enrich(scraped_data, url)
    print(f"    [✓] Done: {result['company_name']}")

    return result


# ========= MAIN EXECUTION =========

if __name__ == "__main__":
    print("=" * 60)
    print("  🏆 COMPANY ENRICHMENT PIPELINE")
    print("=" * 60)
    print()
    print("Enter a JSON array of company URLs.")
    print('Example: ["https://www.stripe.com", "https://www.hubspot.com"]')
    print()

    # 👉 Input: Prompt for URLs
    url_input = input("Paste your URL array here: ")

    # Parse input
    try:
        urls = json.loads(url_input)
        if not isinstance(urls, list):
            urls = [urls]
    except json.JSONDecodeError:
        # Handle comma-separated or single URL
        urls = [u.strip().strip('"').strip("'") for u in url_input.split(',')]

    print(f"\n[*] Processing {len(urls)} URLs...\n")

    results = []
    for url in urls:
        try:
            data = enrich_company(url)
            results.append(data)
        except Exception as e:
            print(f"  Error processing {url}: {e}")
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

    # Save results to JSON file
    with open('results.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\n[✓] Results saved to results.json")

    # Print results for evaluation
    print("\n=== FINAL OUTPUT ===\n")
    print(json.dumps(results, indent=2, ensure_ascii=False))

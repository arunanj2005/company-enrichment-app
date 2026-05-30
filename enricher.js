const OpenAI = require('openai');

let openai = null;

function getClient() {
  if (!openai) {
    const apiKey = process.env.OPENROUTER_API_KEY || process.env.OPENAI_API_KEY;
    if (!apiKey || apiKey === 'your-openai-api-key-here' || apiKey === 'sk-placeholder-add-your-key') {
      return null;
    }
    openai = new OpenAI({
      apiKey,
      baseURL: 'https://openrouter.ai/api/v1',
    });
  }
  return openai;
}

/**
 * Truncate text to fit within token budget
 * Rough estimate: 1 token ≈ 4 characters
 */
function truncateForTokens(text, maxTokens = 3000) {
  const maxChars = maxTokens * 4;
  if (text.length <= maxChars) return text;
  return text.slice(0, maxChars) + '\n[...truncated for token optimization]';
}

/**
 * Prepare scraped data for the LLM - optimize tokens
 */
function prepareContext(scrapedData) {
  const { rawTexts, contactInfo, meta } = scrapedData;

  // Combine texts with separator, truncate each page
  const combinedText = rawTexts
    .map((text, i) => {
      const truncated = truncateForTokens(text, 1500);
      return `--- Page ${i + 1} ---\n${truncated}`;
    })
    .join('\n\n');

  // Build context string
  let context = '';
  if (meta.title) context += `Website Title: ${meta.title}\n`;
  if (meta.description) context += `Meta Description: ${meta.description}\n`;
  if (meta.siteName) context += `Site Name: ${meta.siteName}\n`;
  if (contactInfo.emails.length > 0) context += `Found Emails: ${contactInfo.emails.join(', ')}\n`;
  if (contactInfo.phones.length > 0) context += `Found Phones: ${contactInfo.phones.join(', ')}\n`;
  context += `\n--- Scraped Content ---\n${combinedText}`;

  // Final truncation to stay within budget
  return truncateForTokens(context, 6000);
}

/**
 * Use AI to generate enriched company profile
 */
async function enrichCompany(scrapedData, websiteUrl) {
  const context = prepareContext(scrapedData);

  const systemPrompt = `You are a business intelligence analyst. Your job is to extract and infer company information from scraped website data. 

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
}`;

  const userPrompt = `Analyze this company website data and extract a business profile.

Website URL: ${websiteUrl}

${context}

Return ONLY the JSON object, no markdown formatting, no code blocks.`;

  try {
    const client = getClient();
    if (!client) {
      console.error('[Enricher] No OpenAI API key configured');
      const meta = scrapedData.meta || {};
      const contact = scrapedData.contactInfo || {};
      return {
        website_name: meta.title || 'N/A',
        company_name: meta.siteName || meta.title || 'N/A',
        address: 'N/A',
        mobile_number: contact.phones?.[0] || 'N/A',
        mail: contact.emails || [],
        core_service: meta.description || 'N/A',
        target_customer: 'N/A',
        probable_pain_point: 'N/A',
        outreach_opener: 'N/A',
      };
    }

    const response = await client.chat.completions.create({
      model: 'openai/gpt-4o-mini',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt }
      ],
      temperature: 0.3,
      max_tokens: 800,
    });

    const content = response.choices[0].message.content;
    // Handle potential markdown wrapping
    let jsonStr = content.trim();
    if (jsonStr.startsWith('```')) {
      jsonStr = jsonStr.replace(/^```(?:json)?\n?/, '').replace(/\n?```$/, '');
    }
    const parsed = JSON.parse(jsonStr);

    // Ensure schema compliance
    return {
      website_name: parsed.website_name || 'N/A',
      company_name: parsed.company_name || 'N/A',
      address: parsed.address || 'N/A',
      mobile_number: parsed.mobile_number || 'N/A',
      mail: Array.isArray(parsed.mail) ? parsed.mail : [],
      core_service: parsed.core_service || 'N/A',
      target_customer: parsed.target_customer || 'N/A',
      probable_pain_point: parsed.probable_pain_point || 'N/A',
      outreach_opener: parsed.outreach_opener || 'N/A',
    };
  } catch (err) {
    console.error(`[Enricher] AI enrichment failed: ${err.message}`);
    // Return a safe fallback
    return {
      website_name: scrapedData.meta?.title || 'N/A',
      company_name: scrapedData.meta?.siteName || 'N/A',
      address: 'N/A',
      mobile_number: scrapedData.contactInfo?.phones?.[0] || 'N/A',
      mail: scrapedData.contactInfo?.emails || [],
      core_service: scrapedData.meta?.description || 'N/A',
      target_customer: 'N/A',
      probable_pain_point: 'N/A',
      outreach_opener: 'N/A',
    };
  }
}

module.exports = { enrichCompany, prepareContext };

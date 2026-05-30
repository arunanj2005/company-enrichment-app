const fs = require('fs');
const path = require('path');

const DB_PATH = path.join(__dirname, 'data.json');

function readData() {
  try {
    if (fs.existsSync(DB_PATH)) {
      const raw = fs.readFileSync(DB_PATH, 'utf-8');
      return JSON.parse(raw);
    }
  } catch (err) {
    console.error('[DB] Error reading data:', err.message);
  }
  return { companies: [] };
}

function writeData(data) {
  fs.writeFileSync(DB_PATH, JSON.stringify(data, null, 2), 'utf-8');
}

function saveCompany(url, enrichedData) {
  const data = readData();
  data.companies.push({
    id: Date.now(),
    url,
    ...enrichedData,
    created_at: new Date().toISOString(),
  });
  writeData(data);
}

function getAllCompanies() {
  const data = readData();
  return data.companies.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
}

function getCompanyByUrl(url) {
  const data = readData();
  return data.companies.find(c => c.url === url) || null;
}

module.exports = { saveCompany, getAllCompanies, getCompanyByUrl };

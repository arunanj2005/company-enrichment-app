/**
 * Seed script - initializes data.json if it doesn't exist.
 * Run: node seed-data.js
 * 
 * On deployment, this ensures the app has an empty but valid data file.
 * Pre-enriched data should be added by running the app and using the /enrichInput endpoint.
 */

const fs = require('fs');
const path = require('path');

const DB_PATH = path.join(__dirname, 'data.json');

if (!fs.existsSync(DB_PATH)) {
  fs.writeFileSync(DB_PATH, JSON.stringify({ companies: [] }, null, 2));
  console.log('Created empty data.json');
} else {
  console.log('data.json already exists, skipping seed.');
}

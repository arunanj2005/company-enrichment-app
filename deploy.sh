#!/bin/bash
# Deploy to Railway
# Run: chmod +x deploy.sh && ./deploy.sh

echo "=== Company Enrichment App Deployment ==="
echo ""

# Check if railway is logged in
if ! railway whoami &>/dev/null; then
  echo "Logging into Railway..."
  railway login
fi

echo ""
echo "Creating Railway project..."
railway init --name company-enrichment-app

echo ""
echo "Setting environment variables..."
read -p "Enter your OpenAI API Key: " OPENAI_KEY
railway variables set OPENAI_API_KEY="$OPENAI_KEY"
railway variables set PORT=3001
railway variables set NODE_ENV=production

echo ""
echo "Deploying..."
railway up --detach

echo ""
echo "Generating public domain..."
railway domain

echo ""
echo "=== Deployment complete! ==="
echo "Your app will be live in ~2 minutes at the URL above."
echo "Run 'railway logs' to monitor deployment."

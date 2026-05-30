import React, { useState } from 'react';
import CompanyCard from './CompanyCard';
import LoadingSpinner from './LoadingSpinner';
import './EnrichSection.css';

function EnrichSection({ onSuccess }) {
  const [url, setUrl] = useState('');
  const [websiteName, setWebsiteName] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  const handleEnrich = async (e) => {
    e.preventDefault();
    if (!url.trim()) {
      setError('Please enter a company URL');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);
    setStatus('Scraping website...');

    try {
      const response = await fetch('/enrichInput', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim(), website_name: websiteName.trim() }),
      });

      setStatus('Analyzing with AI...');

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Enrichment failed');
      }

      const data = await response.json();
      setResult(data);
      setStatus('');
      onSuccess();
    } catch (err) {
      setError(err.message || 'Something went wrong');
      setStatus('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="enrich-section">
      <div className="enrich-form-container">
        <h2 className="section-title">Enrich a Company</h2>
        <p className="section-desc">
          Enter a company website URL to extract business intelligence using AI.
        </p>

        <form onSubmit={handleEnrich} className="enrich-form">
          <div className="form-group">
            <label htmlFor="website-name" className="form-label">
              Website Name (optional)
            </label>
            <input
              id="website-name"
              type="text"
              className="form-input"
              placeholder="e.g., Acme Corp"
              value={websiteName}
              onChange={(e) => setWebsiteName(e.target.value)}
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="company-url" className="form-label">
              Company URL *
            </label>
            <input
              id="company-url"
              type="text"
              className="form-input"
              placeholder="e.g., https://www.example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={loading}
              required
            />
          </div>

          <button type="submit" className="enrich-btn" disabled={loading}>
            {loading ? 'Processing...' : '✨ Enrich Company'}
          </button>
        </form>

        {loading && <LoadingSpinner status={status} />}
        {error && <div className="error-message">❌ {error}</div>}
      </div>

      {result && (
        <div className="enrich-result">
          <h3 className="result-title">✅ Enrichment Result</h3>
          <CompanyCard company={result} />
        </div>
      )}
    </div>
  );
}

export default EnrichSection;

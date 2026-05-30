import React, { useState, useEffect } from 'react';
import CompanyCard from './CompanyCard';
import LoadingSpinner from './LoadingSpinner';
import './ResultsSection.css';

function ResultsSection() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [loaded, setLoaded] = useState(false);

  const fetchResults = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch('/results');
      if (!response.ok) throw new Error('Failed to fetch results');
      const data = await response.json();
      setResults(data);
      setLoaded(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, []);

  return (
    <div className="results-section">
      <div className="results-header">
        <h2 className="section-title">All Enriched Companies</h2>
        <button className="refresh-btn" onClick={fetchResults} disabled={loading}>
          🔄 {loading ? 'Loading...' : 'Show All Results'}
        </button>
      </div>

      {loading && <LoadingSpinner status="Fetching results..." />}
      {error && <div className="error-message">❌ {error}</div>}

      {loaded && !loading && results.length === 0 && (
        <div className="empty-state">
          <p>📭 No enriched companies yet. Go to the Enrich tab to add some!</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="results-grid">
          {results.map((company, index) => (
            <CompanyCard key={company.id || index} company={company} />
          ))}
        </div>
      )}

      {loaded && results.length > 0 && (
        <p className="results-count">
          Showing {results.length} enriched {results.length === 1 ? 'company' : 'companies'}
        </p>
      )}
    </div>
  );
}

export default ResultsSection;

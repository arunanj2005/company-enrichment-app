import React, { useState } from 'react';
import EnrichSection from './components/EnrichSection';
import ResultsSection from './components/ResultsSection';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('enrich');
  const [refreshKey, setRefreshKey] = useState(0);

  const handleEnrichSuccess = () => {
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1 className="app-title">
            <span className="title-icon">🔍</span>
            Company Enrichment Tool
          </h1>
          <p className="app-subtitle">AI-powered business intelligence from company websites</p>
        </div>
      </header>

      <nav className="tab-nav">
        <button
          className={`tab-btn ${activeTab === 'enrich' ? 'active' : ''}`}
          onClick={() => setActiveTab('enrich')}
        >
          ✨ Enrich Company
        </button>
        <button
          className={`tab-btn ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
        >
          📊 All Results
        </button>
      </nav>

      <main className="app-main">
        {activeTab === 'enrich' && (
          <EnrichSection onSuccess={handleEnrichSuccess} />
        )}
        {activeTab === 'results' && (
          <ResultsSection key={refreshKey} />
        )}
      </main>

      <footer className="app-footer">
        <p>Company Enrichment Tool — Powered by AI</p>
      </footer>
    </div>
  );
}

export default App;

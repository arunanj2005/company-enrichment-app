import React from 'react';
import './LoadingSpinner.css';

function LoadingSpinner({ status }) {
  return (
    <div className="loading-container">
      <div className="spinner"></div>
      {status && <p className="loading-status">{status}</p>}
      <div className="loading-steps">
        <div className="step active">
          <span className="step-dot"></span>
          <span>Fetching website data</span>
        </div>
        <div className="step">
          <span className="step-dot"></span>
          <span>Extracting relevant pages</span>
        </div>
        <div className="step">
          <span className="step-dot"></span>
          <span>Analyzing with AI</span>
        </div>
        <div className="step">
          <span className="step-dot"></span>
          <span>Generating insights</span>
        </div>
      </div>
    </div>
  );
}

export default LoadingSpinner;

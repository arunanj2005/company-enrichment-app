import React, { useState, useEffect } from 'react';
import './LoadingSpinner.css';

function LoadingSpinner({ status }) {
  const [elapsed, setElapsed] = useState(0);
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(prev => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    // Progress through steps based on time
    if (elapsed >= 2) setStep(1);
    if (elapsed >= 5) setStep(2);
    if (elapsed >= 8) setStep(3);
  }, [elapsed]);

  const steps = [
    'Fetching website data...',
    'Extracting relevant pages...',
    'Analyzing content with AI...',
    'Generating business insights...',
  ];

  return (
    <div className="loading-container" role="status" aria-live="polite">
      <div className="spinner"></div>
      <p className="loading-status">{status || steps[step]}</p>
      <p className="loading-elapsed">{elapsed}s elapsed</p>
      <div className="loading-steps">
        {steps.map((s, i) => (
          <div key={i} className={`step ${i <= step ? 'active' : ''} ${i < step ? 'done' : ''}`}>
            <span className="step-dot">{i < step ? '✓' : ''}</span>
            <span>{s}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default LoadingSpinner;

import React, { useState } from 'react';
import './CompanyCard.css';

function CompanyCard({ company }) {
  const [expanded, setExpanded] = useState(false);

  const renderEmails = (mail) => {
    if (!mail || (Array.isArray(mail) && mail.length === 0)) return 'N/A';
    const emails = Array.isArray(mail) ? mail : [mail];
    return emails.map((email, i) => (
      <a key={i} href={`mailto:${email}`} className="email-link">
        {email}
      </a>
    ));
  };

  return (
    <div className="company-card">
      <div className="card-header" onClick={() => setExpanded(!expanded)}>
        <div className="card-title-row">
          <h3 className="card-company-name">{company.company_name || 'N/A'}</h3>
          <span className="expand-icon">{expanded ? '▼' : '▶'}</span>
        </div>
        <p className="card-website-name">{company.website_name || 'N/A'}</p>
        {company.url && <p className="card-url">{company.url}</p>}
      </div>

      <div className={`card-body ${expanded ? 'expanded' : ''}`}>
        <div className="card-grid">
          <div className="card-field">
            <span className="field-label">📍 Address</span>
            <span className="field-value">{company.address || 'N/A'}</span>
          </div>

          <div className="card-field">
            <span className="field-label">📞 Phone</span>
            <span className="field-value">{company.mobile_number || 'N/A'}</span>
          </div>

          <div className="card-field">
            <span className="field-label">📧 Email(s)</span>
            <span className="field-value email-list">
              {renderEmails(company.mail)}
            </span>
          </div>

          <div className="card-field full-width">
            <span className="field-label">🎯 Core Service</span>
            <span className="field-value">{company.core_service || 'N/A'}</span>
          </div>

          <div className="card-field full-width">
            <span className="field-label">👥 Target Customer</span>
            <span className="field-value">{company.target_customer || 'N/A'}</span>
          </div>

          <div className="card-field full-width">
            <span className="field-label">⚡ Probable Pain Point</span>
            <span className="field-value">{company.probable_pain_point || 'N/A'}</span>
          </div>

          <div className="card-field full-width outreach">
            <span className="field-label">💬 Outreach Opener</span>
            <span className="field-value outreach-text">
              {company.outreach_opener || 'N/A'}
            </span>
          </div>
        </div>
      </div>

      {!expanded && (
        <div className="card-preview">
          <span className="preview-service">{company.core_service || 'N/A'}</span>
        </div>
      )}
    </div>
  );
}

export default CompanyCard;

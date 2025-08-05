import React, { useState } from 'react';
import './AIInsights.css';

const AIInsights = ({ insights }) => {
  const [activeTab, setActiveTab] = useState('summary');

  if (!insights || Object.keys(insights).length === 0) {
    return (
      <div className="ai-insights">
        <div className="insights-header">
          <h3>🤖 AI Insights</h3>
          <p>No insights available for this document</p>
        </div>
      </div>
    );
  }

  const renderSummary = () => {
    const summary = insights.document_summary;
    if (!summary) return <p>No summary available</p>;

    return (
      <div className="insight-section">
        <div className="summary-content">
          <p className="summary-text">{summary.summary}</p>
          <div className="confidence-indicator">
            <span className="confidence-label">Confidence:</span>
            <div className="confidence-bar">
              <div 
                className="confidence-fill" 
                style={{ width: `${(summary.confidence || 0) * 100}%` }}
              ></div>
            </div>
            <span className="confidence-value">{((summary.confidence || 0) * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>
    );
  };

  const renderSentiment = () => {
    const sentiment = insights.sentiment_analysis;
    if (!sentiment) return <p>No sentiment analysis available</p>;
    
    const getSentimentColor = (sent) => {
      switch (sent) {
        case 'POSITIVE': return '#27ae60';
        case 'NEGATIVE': return '#e74c3c';
        case 'MIXED': return '#f39c12';
        default: return '#95a5a6';
      }
    };

    return (
      <div className="insight-section">
        <div className="sentiment-overview">
          <div className="sentiment-main">
            <span 
              className="sentiment-badge"
              style={{ backgroundColor: getSentimentColor(sentiment.sentiment) }}
            >
              {sentiment.sentiment}
            </span>
            <span className="sentiment-confidence">
              {((sentiment.confidence || 0) * 100).toFixed(0)}% confidence
            </span>
          </div>
          
          <div className="sentiment-scores">
            {Object.entries(sentiment.scores || {}).map(([key, value]) => (
              <div key={key} className="score-item">
                <span className="score-label">{key}</span>
                <div className="score-bar">
                  <div 
                    className="score-fill"
                    style={{ 
                      width: `${value * 100}%`,
                      backgroundColor: getSentimentColor(key)
                    }}
                  ></div>
                </div>
                <span className="score-value">{(value * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderKeyPhrases = () => {
    const phrases = insights.key_phrases;
    if (!phrases || !phrases.phrases || phrases.phrases.length === 0) {
      return <p>No key phrases detected</p>;
    }

    return (
      <div className="insight-section">
        <div className="phrases-grid">
          {phrases.phrases.map((phrase, index) => (
            <div key={index} className="phrase-item">
              <span className="phrase-text">{phrase.text}</span>
              <span className="phrase-confidence">
                {(phrase.confidence * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
        {phrases.total_found > phrases.phrases.length && (
          <p className="phrases-note">
            Showing top {phrases.phrases.length} of {phrases.total_found} phrases
          </p>
        )}
      </div>
    );
  };

  const renderEntities = () => {
    const entities = insights.entities;
    if (!entities || !entities.entities_by_type || Object.keys(entities.entities_by_type).length === 0) {
      return <p>No entities detected</p>;
    }

    return (
      <div className="insight-section">
        <div className="entities-container">
          {Object.entries(entities.entities_by_type).map(([type, entityList]) => (
            <div key={type} className="entity-group">
              <h4 className="entity-type">{type.replace('_', ' ')}</h4>
              <div className="entity-list">
                {entityList.map((entity, index) => (
                  <div key={index} className="entity-item">
                    <span className="entity-text">{entity.text}</span>
                    <span className="entity-confidence">
                      {(entity.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderBusinessInsights = () => {
    const business = insights.business_insights;
    if (!business) return <p>No business insights available</p>;

    return (
      <div className="insight-section">
        <div className="business-insights">
          {business.key_insights && business.key_insights.length > 0 && (
            <div className="insight-group">
              <h4>💡 Key Insights</h4>
              <ul>
                {business.key_insights.map((insight, index) => (
                  <li key={index}>{insight}</li>
                ))}
              </ul>
            </div>
          )}

          {business.financial_highlights && business.financial_highlights.length > 0 && (
            <div className="insight-group">
              <h4>💰 Financial Highlights</h4>
              <ul>
                {business.financial_highlights.map((highlight, index) => (
                  <li key={index}>{highlight}</li>
                ))}
              </ul>
            </div>
          )}

          {business.action_items && business.action_items.length > 0 && (
            <div className="insight-group">
              <h4>✅ Action Items</h4>
              <ul>
                {business.action_items.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {business.risk_factors && business.risk_factors.length > 0 && (
            <div className="insight-group">
              <h4>⚠️ Risk Factors</h4>
              <ul>
                {business.risk_factors.map((risk, index) => (
                  <li key={index}>{risk}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    );
  };

  const tabs = [
    { id: 'summary', label: '📄 Summary', content: renderSummary },
    { id: 'sentiment', label: '😊 Sentiment', content: renderSentiment },
    { id: 'phrases', label: '🔑 Key Phrases', content: renderKeyPhrases },
    { id: 'entities', label: '🏷️ Entities', content: renderEntities },
    { id: 'business', label: '💼 Business', content: renderBusinessInsights }
  ];

  return (
    <div className="ai-insights">
      <div className="insights-header">
        <h3>🤖 AI Insights & Analysis</h3>
        <p>Powered by Amazon Comprehend & Claude AI</p>
      </div>

      <div className="insights-tabs">
        <div className="tab-buttons">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="tab-content">
          {tabs.find(tab => tab.id === activeTab)?.content()}
        </div>
      </div>
    </div>
  );
};

export default AIInsights;
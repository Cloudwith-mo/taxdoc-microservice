import React from 'react';
import './MarketingFeatures.css';

const MarketingFeatures = () => {
  const uniqueFeatures = [
    {
      icon: '🤖',
      title: 'AI Summary & Insights',
      description: '3-bullet "So-What?" insights that management loves',
      status: 'Live',
      highlight: 'Parseur can\'t do this',
      details: [
        'Automatic document summarization',
        'Business impact analysis',
        'Action item extraction',
        'Risk factor identification'
      ]
    },
    {
      icon: '😊',
      title: 'Universal Sentiment Analysis',
      description: 'Works on complaint letters, HR reports - beyond templates',
      status: 'Live',
      highlight: 'Outside Parseur\'s comfort zone',
      details: [
        'Any document type supported',
        'Emotional context detection',
        'Confidence scoring',
        'Multi-language support'
      ]
    },
    {
      icon: '💬',
      title: 'Chatbot Q&A',
      description: 'Ask questions about your documents in natural language',
      status: 'Coming Soon',
      highlight: 'FOMO lead magnet',
      details: [
        'Natural language queries',
        'Document-specific answers',
        'Cross-document insights',
        'Export conversations'
      ]
    },
    {
      icon: '📊',
      title: 'Advanced Analytics Dashboard',
      description: 'Processing insights and trends Parseur doesn\'t offer',
      status: 'Coming Soon',
      highlight: 'Enterprise exclusive',
      details: [
        'Processing success rates',
        'Document type trends',
        'Cost optimization insights',
        'Team productivity metrics'
      ]
    }
  ];

  return (
    <div className="marketing-features">
      <div className="features-header">
        <h2>🚀 Why Dr.Doc Beats Parseur</h2>
        <p>Features that set us apart from the competition</p>
      </div>

      <div className="features-grid">
        {uniqueFeatures.map((feature, index) => (
          <div key={index} className={`feature-card ${feature.status.toLowerCase().replace(' ', '-')}`}>
            <div className="feature-header">
              <div className="feature-icon">{feature.icon}</div>
              <div className="feature-title-section">
                <h3>{feature.title}</h3>
                <span className={`status-badge ${feature.status.toLowerCase().replace(' ', '-')}`}>
                  {feature.status}
                </span>
              </div>
            </div>

            <p className="feature-description">{feature.description}</p>

            <div className="feature-highlight">
              <span className="highlight-badge">{feature.highlight}</span>
            </div>

            <ul className="feature-details">
              {feature.details.map((detail, idx) => (
                <li key={idx}>{detail}</li>
              ))}
            </ul>

            {feature.status === 'Coming Soon' && (
              <div className="coming-soon-cta">
                <button className="notify-btn">
                  🔔 Notify Me When Ready
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="competitive-advantage">
        <h3>📈 Our Competitive Edge</h3>
        <div className="advantage-grid">
          <div className="advantage-item">
            <div className="advantage-metric">≥92%</div>
            <div className="advantage-label">Field Accuracy</div>
            <div className="advantage-note">Beats Parseur's 90-95%</div>
          </div>
          <div className="advantage-item">
            <div className="advantage-metric">11+</div>
            <div className="advantage-label">Document Types</div>
            <div className="advantage-note">Universal processing</div>
          </div>
          <div className="advantage-item">
            <div className="advantage-metric">3-Layer</div>
            <div className="advantage-label">AI Pipeline</div>
            <div className="advantage-note">Textract + Claude + Regex</div>
          </div>
          <div className="advantage-item">
            <div className="advantage-metric">60%</div>
            <div className="advantage-label">Cost Savings</div>
            <div className="advantage-note">Smart caching & routing</div>
          </div>
        </div>
      </div>

      <div className="roadmap-teaser">
        <h3>🗺️ Coming Next Quarter</h3>
        <div className="roadmap-items">
          <div className="roadmap-item">
            <span className="roadmap-icon">🤖</span>
            <span className="roadmap-text">Custom ML model training</span>
          </div>
          <div className="roadmap-item">
            <span className="roadmap-icon">🌍</span>
            <span className="roadmap-text">Multi-language support</span>
          </div>
          <div className="roadmap-item">
            <span className="roadmap-icon">📱</span>
            <span className="roadmap-text">Mobile app launch</span>
          </div>
          <div className="roadmap-item">
            <span className="roadmap-icon">🔗</span>
            <span className="roadmap-text">API integrations hub</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketingFeatures;
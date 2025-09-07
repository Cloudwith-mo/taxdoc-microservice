import React from 'react';

const FeatureStatus = () => {
  const features = [
    {
      category: 'Register (Cognito)',
      status: '✅ Complete',
      items: ['User registration', 'Login/logout', 'JWT tokens']
    },
    {
      category: 'Upload',
      status: '✅ Complete',
      items: ['Drag & Drop ✅', 'Batch ✅', 'Email ✅']
    },
    {
      category: 'Extract (Highest Priority)',
      status: '✅ Complete',
      items: ['W/ AI ✅', 'Enable edit ✅', 'Extract any doc (V3) ✅']
    },
    {
      category: 'Download',
      status: '✅ Complete',
      items: ['CSV, Json, Excel ✅', 'Email to: ✅']
    },
    {
      category: 'SNS (Alert)',
      status: '✅ Complete',
      items: ['Processing notifications', 'Status updates']
    },
    {
      category: 'Pay (Stripe)',
      status: '✅ Complete',
      items: ['Subscription checkout', 'Webhook handling']
    },
    {
      category: 'AI Chatbot',
      status: '✅ Complete',
      items: ['Doc specific questions ✅', 'Generic questions ✅']
    }
  ];

  return (
    <div className="feature-status-container">
      <h2>🚀 Platform Features Status</h2>
      <div className="features-grid">
        {features.map((feature, index) => (
          <div key={index} className="feature-card">
            <div className="feature-header">
              <h3>{feature.category}</h3>
              <span className={`status ${feature.status.includes('✅') ? 'complete' : 'pending'}`}>
                {feature.status}
              </span>
            </div>
            <ul className="feature-items">
              {feature.items.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      
      <div className="platform-links">
        <a href="http://taxdoc-mvp-web-1754513919.s3-website-us-east-1.amazonaws.com/mvp2-enhanced.html" 
           target="_blank" rel="noopener noreferrer" className="platform-link">
          🌐 Live Platform
        </a>
        <a href="https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod" 
           target="_blank" rel="noopener noreferrer" className="api-link">
          🔗 API Endpoint
        </a>
      </div>
    </div>
  );
};

export default FeatureStatus;
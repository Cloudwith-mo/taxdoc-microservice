import React, { useState } from 'react';
import './AnalyticsDashboard.css';

const AnalyticsDashboard = () => {
  const [notifyEmail, setNotifyEmail] = useState('');
  const [showNotify, setShowNotify] = useState(false);

  const handleNotifySubmit = (e) => {
    e.preventDefault();
    localStorage.setItem('analytics_notify_email', notifyEmail);
    setShowNotify(false);
    alert('Thanks! We\'ll notify you when Advanced Analytics is ready.');
  };

  const mockMetrics = [
    { label: 'Processing Success Rate', value: '94.7%', trend: '+2.3%' },
    { label: 'Average Processing Time', value: '2.4s', trend: '-0.8s' },
    { label: 'Documents Processed', value: '1,247', trend: '+156' },
    { label: 'Cost per Document', value: '$0.12', trend: '-$0.03' }
  ];

  const documentTypes = [
    { type: 'W-2', count: 423, percentage: 34 },
    { type: '1099-NEC', count: 298, percentage: 24 },
    { type: 'Bank Statements', count: 187, percentage: 15 },
    { type: 'Receipts', count: 156, percentage: 12 },
    { type: 'Other', count: 183, percentage: 15 }
  ];

  return (
    <div className="analytics-dashboard">
      <div className="dashboard-header">
        <h3>📊 Advanced Analytics Dashboard</h3>
        <div className="feature-badge coming-soon">COMING SOON</div>
        <div className="enterprise-badge">ENTERPRISE EXCLUSIVE</div>
      </div>

      <div className="dashboard-preview">
        <div className="preview-description">
          <h4>Processing insights and trends Parseur doesn't offer</h4>
          <div className="feature-list">
            <div className="feature-item">📈 Processing success rates</div>
            <div className="feature-item">📋 Document type trends</div>
            <div className="feature-item">💰 Cost optimization insights</div>
            <div className="feature-item">👥 Team productivity metrics</div>
          </div>
        </div>

        <div className="demo-dashboard">
          <div className="metrics-grid">
            {mockMetrics.map((metric, index) => (
              <div key={index} className="metric-card">
                <div className="metric-value">{metric.value}</div>
                <div className="metric-label">{metric.label}</div>
                <div className="metric-trend positive">{metric.trend}</div>
              </div>
            ))}
          </div>

          <div className="charts-section">
            <div className="chart-card">
              <h5>Document Type Distribution</h5>
              <div className="chart-placeholder">
                {documentTypes.map((item, index) => (
                  <div key={index} className="chart-bar">
                    <div className="bar-label">{item.type}</div>
                    <div className="bar-container">
                      <div 
                        className="bar-fill" 
                        style={{ width: `${item.percentage}%` }}
                      ></div>
                    </div>
                    <div className="bar-value">{item.count}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="chart-card">
              <h5>Processing Trends (Last 30 Days)</h5>
              <div className="trend-chart">
                <div className="trend-line"></div>
                <div className="trend-points">
                  {[...Array(30)].map((_, i) => (
                    <div 
                      key={i} 
                      className="trend-point" 
                      style={{ 
                        left: `${(i / 29) * 100}%`,
                        bottom: `${Math.random() * 60 + 20}%`
                      }}
                    ></div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="notify-section">
          <button 
            className="notify-btn enterprise"
            onClick={() => setShowNotify(true)}
          >
            🔔 Notify Me When Ready
          </button>
        </div>
      </div>

      {showNotify && (
        <div className="notify-modal">
          <div className="notify-content">
            <h4>Enterprise Analytics Preview</h4>
            <p>Get early access to advanced analytics and insights!</p>
            <form onSubmit={handleNotifySubmit}>
              <input
                type="email"
                placeholder="Enter your business email"
                value={notifyEmail}
                onChange={(e) => setNotifyEmail(e.target.value)}
                required
              />
              <div className="notify-actions">
                <button type="submit">Get Early Access</button>
                <button type="button" onClick={() => setShowNotify(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalyticsDashboard;
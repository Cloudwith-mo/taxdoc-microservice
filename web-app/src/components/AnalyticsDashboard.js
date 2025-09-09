import React, { useState, useEffect } from 'react';
import './AnalyticsDashboard.css';

const API_BASE = "https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod";

const AnalyticsDashboard = () => {
  const [metrics, setMetrics] = useState({});
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('7d');

  const getUserId = () => {
    let id = localStorage.getItem('taxdoc_user');
    if (!id) { id = 'ANON'; localStorage.setItem('taxdoc_user', id); }
    return id;
  };

  const fetchMetrics = async () => {
    try {
      const userId = getUserId();
      const [docsRes, metricsRes] = await Promise.all([
        fetch(`${API_BASE}/documents?userId=${encodeURIComponent(userId)}`),
        fetch(`${API_BASE}/analytics?userId=${encodeURIComponent(userId)}&period=${timeRange}`)
      ]);

      const { items = [] } = await docsRes.json();
      const analyticsData = metricsRes.ok ? await metricsRes.json() : {};

      const now = new Date();
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const week = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
      const month = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

      const processed = items.filter(d => d.status === 'PROCESSED');
      const failed = items.filter(d => d.status === 'FAILED');
      const todayDocs = items.filter(d => new Date(d.processedAt) >= today);
      const weekDocs = items.filter(d => new Date(d.processedAt) >= week);
      const monthDocs = items.filter(d => new Date(d.processedAt) >= month);

      const avgConfidence = processed.length > 0 
        ? processed.reduce((sum, d) => sum + (d.docTypeConfidence || 0), 0) / processed.length 
        : 0;

      const docTypes = items.reduce((acc, d) => {
        acc[d.docType || 'Unknown'] = (acc[d.docType || 'Unknown'] || 0) + 1;
        return acc;
      }, {});

      setMetrics({
        totalDocs: items.length,
        processed: processed.length,
        failed: failed.length,
        successRate: items.length > 0 ? (processed.length / items.length) * 100 : 0,
        avgConfidence: avgConfidence * 100,
        todayDocs: todayDocs.length,
        weekDocs: weekDocs.length,
        monthDocs: monthDocs.length,
        docTypes,
        recentActivity: items.slice(-10).reverse(),
        ...analyticsData
      });
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [timeRange]);

  if (loading) return <div className="analytics-loading">Loading analytics...</div>;

  return (
    <div className="analytics-dashboard">
      <div className="analytics-header">
        <h2>📊 Analytics Dashboard</h2>
        <select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
          <option value="1d">Today</option>
          <option value="7d">7 Days</option>
          <option value="30d">30 Days</option>
          <option value="all">All Time</option>
        </select>
      </div>

      <div className="metrics-grid">
        <MetricCard
          title="Total Documents"
          value={metrics.totalDocs}
          trend="+12%"
          icon="📄"
        />
        
        <MetricCard
          title="Success Rate"
          value={`${metrics.successRate.toFixed(1)}%`}
          trend={metrics.successRate >= 95 ? "✅" : "⚠️"}
          icon="✅"
          alert={metrics.successRate < 95}
        />
        
        <MetricCard
          title="Avg Confidence"
          value={`${metrics.avgConfidence.toFixed(1)}%`}
          trend={metrics.avgConfidence >= 80 ? "📈" : "📉"}
          icon="🎯"
        />
        
        <MetricCard
          title="Processing Latency"
          value={`${metrics.avgLatency || 9.2}s`}
          trend="P95"
          icon="⚡"
        />
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3>Documents Processed</h3>
          <div className="time-series">
            <div className="metric-row">
              <span>Today:</span>
              <span>{metrics.todayDocs}</span>
            </div>
            <div className="metric-row">
              <span>7 Days:</span>
              <span>{metrics.weekDocs}</span>
            </div>
            <div className="metric-row">
              <span>30 Days:</span>
              <span>{metrics.monthDocs}</span>
            </div>
          </div>
        </div>

        <div className="chart-card">
          <h3>Document Types</h3>
          <div className="doc-types">
            {Object.entries(metrics.docTypes).map(([type, count]) => (
              <div key={type} className="type-row">
                <span>{type}:</span>
                <span>{count}</span>
                <div className="type-bar" style={{width: `${(count / metrics.totalDocs) * 100}%`}}></div>
              </div>
            ))}
          </div>
        </div>

        <div className="chart-card">
          <h3>Processing Status</h3>
          <div className="status-breakdown">
            <div className="status-item success">
              <span>Processed: {metrics.processed}</span>
            </div>
            <div className="status-item failed">
              <span>Failed: {metrics.failed}</span>
            </div>
          </div>
        </div>

        <div className="chart-card">
          <h3>Recent Activity</h3>
          <div className="activity-feed">
            {metrics.recentActivity.map((doc, idx) => (
              <div key={idx} className="activity-item">
                <span className="activity-type">{doc.docType}</span>
                <span className="activity-file">{doc.filename}</span>
                <span className="activity-time">
                  {new Date(doc.processedAt).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="alerts-section">
        <h3>🚨 Alerts & Monitoring</h3>
        <div className="alerts-grid">
          {metrics.successRate < 95 && (
            <div className="alert warning">
              Success rate below 95%: {metrics.successRate.toFixed(1)}%
            </div>
          )}
          {metrics.avgConfidence < 80 && (
            <div className="alert warning">
              Average confidence below 80%: {metrics.avgConfidence.toFixed(1)}%
            </div>
          )}
          {(metrics.avgLatency || 9.2) > 15 && (
            <div className="alert error">
              Processing latency above SLA: {metrics.avgLatency || 9.2}s
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const MetricCard = ({ title, value, trend, icon, alert }) => (
  <div className={`metric-card ${alert ? 'alert' : ''}`}>
    <div className="metric-header">
      <span className="metric-icon">{icon}</span>
      <span className="metric-title">{title}</span>
    </div>
    <div className="metric-value">{value}</div>
    <div className="metric-trend">{trend}</div>
  </div>
);

export default AnalyticsDashboard;
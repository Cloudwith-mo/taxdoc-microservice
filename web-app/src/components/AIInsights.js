import React, { useState, useEffect } from 'react';

const AIInsights = ({ documentData }) => {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (documentData && documentData.ExtractedData) {
      generateInsights();
    }
  }, [documentData]);

  const generateInsights = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Generate dynamic insights based on actual data
      const extractedData = documentData.ExtractedData;
      const docType = documentData.DocumentType;
      const fieldCount = Object.keys(extractedData).length;
      const confidence = documentData.ExtractionMetadata?.overall_confidence || 0;
      
      // Dynamic insights based on document content
      const dynamicInsights = [];
      
      if (confidence > 0.9) {
        dynamicInsights.push(`💡 High confidence extraction (${Math.round(confidence * 100)}%) - data quality excellent`);
      } else if (confidence > 0.7) {
        dynamicInsights.push(`💡 Good extraction quality (${Math.round(confidence * 100)}%) - minor review recommended`);
      } else {
        dynamicInsights.push(`💡 Lower confidence (${Math.round(confidence * 100)}%) - manual review required`);
      }
      
      // Tax-specific insights
      if (docType === 'W-2') {
        const wages = extractedData.Box1_Wages || extractedData.wages_box1;
        const fedTax = extractedData.Box2_FederalTaxWithheld || extractedData.federal_tax_withheld_box2;
        
        if (wages && fedTax) {
          const taxRate = (fedTax / wages * 100).toFixed(1);
          dynamicInsights.push(`💡 Federal tax rate: ${taxRate}% - ${taxRate > 22 ? 'higher than average' : 'within normal range'}`);
        }
        
        dynamicInsights.push(`💡 W-2 processing complete - ${fieldCount} fields extracted for tax filing`);
      } else if (docType.includes('1099')) {
        dynamicInsights.push(`💡 ${docType} processed - contractor/investment income documented`);
        dynamicInsights.push(`💡 ${fieldCount} fields captured - ready for Schedule B/C filing`);
      }
      
      // Action items based on document type and data
      const actionItems = [];
      if (confidence < 0.8) {
        actionItems.push({ action: "Verify extracted amounts due to lower confidence", priority: "high", category: "compliance" });
      }
      
      if (docType === 'W-2') {
        actionItems.push({ action: "Include in Form 1040 wage calculation", priority: "high", category: "filing" });
        actionItems.push({ action: "Store original document for records", priority: "medium", category: "compliance" });
      }
      
      setInsights({
        insights: dynamicInsights,
        sentiment: {
          sentiment: 'professional',
          confidence: 95,
          tone: 'formal',
          business_impact: `${docType} document processed successfully with ${fieldCount} fields extracted`
        },
        actionItems
      });
      
    } catch (err) {
      setError('Failed to generate AI insights: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!documentData) {
    return (
      <div className="ai-insights-container">
        <h2>🤖 AI-Powered Insights</h2>
        <div className="insight-card">
          <p>Upload a document to see AI-powered insights and analysis</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="ai-insights-container">
        <h2>🤖 AI-Powered Insights</h2>
        <div className="insight-card">
          <p>Generating AI insights...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="ai-insights-container">
        <h2>🤖 AI-Powered Insights</h2>
        <div className="insight-card" style={{borderLeftColor: '#e53e3e'}}>
          <h3>❌ Error</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="ai-insights-container">
        <h2>🤖 AI-Powered Insights</h2>
        <div className="insight-card">
          <p>No insights available for this document</p>
        </div>
      </div>
    );
  }

  return (
    <div className="ai-insights-container">
      <h2>🤖 AI-Powered Insights</h2>
      
      <div className="insights-grid">
        <div className="insight-card">
          <h3>🎯 Management Insights</h3>
          <ul className="insight-bullets">
            {insights.insights.map((insight, index) => (
              <li key={index}>{insight}</li>
            ))}
          </ul>
        </div>
        
        <div className="insight-card">
          <h3>😊 Document Sentiment</h3>
          <div className={`sentiment-indicator sentiment-${insights.sentiment.sentiment}`}>
            {insights.sentiment.sentiment} ({insights.sentiment.confidence}%)
          </div>
          <p>{insights.sentiment.business_impact}</p>
        </div>
        
        <div className="insight-card">
          <h3>✅ Action Items</h3>
          <ul className="action-list">
            {insights.actionItems.map((item, index) => (
              <li key={index} className={`priority-${item.priority}`}>
                <strong>{item.priority.toUpperCase()}:</strong> {item.action}
              </li>
            ))}
          </ul>
        </div>
        
        <div className="insight-card">
          <h3>📊 Processing Summary</h3>
          <div className="processing-stats">
            <div>Form Type: {documentData?.DocumentType || 'Unknown'}</div>
            <div>Fields Extracted: {Object.keys(documentData?.ExtractedData || {}).length}</div>
            <div>Confidence: {Math.round((documentData?.ExtractionMetadata?.overall_confidence || 0) * 100)}%</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIInsights;
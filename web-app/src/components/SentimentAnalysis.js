import React, { useState } from 'react';

const SentimentAnalysis = () => {
  const [text, setText] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyzeSentiment = async () => {
    if (!text.trim()) {
      alert('Please enter text to analyze');
      return;
    }

    setLoading(true);
    
    // Simulate API call
    setTimeout(() => {
      setResults({
        sentiment: 'neutral',
        confidence: 0.87,
        tone: 'professional',
        emotional_indicators: ['professional', 'formal', 'clear'],
        business_impact: 'Document maintains professional tone suitable for business communication'
      });
      setLoading(false);
    }, 1500);
  };

  return (
    <div className="sentiment-analysis-container">
      <h2>😊 Universal Sentiment Analysis</h2>
      <p>Analyze emotional context and tone of any document type</p>
      
      <div className="feature-highlight">
        <h4>✨ Beyond Templates</h4>
        <ul>
          <li>Works on complaint letters, HR reports, any document</li>
          <li>Emotional context detection with confidence scoring</li>
          <li>Multi-language support</li>
          <li>Business impact analysis</li>
        </ul>
      </div>
      
      <div className="sentiment-input-section">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste document text here for sentiment analysis..."
          className="sentiment-textarea"
          rows={8}
        />
        
        <button 
          onClick={analyzeSentiment}
          disabled={loading || !text.trim()}
          className="analyze-button"
        >
          {loading ? 'Analyzing...' : 'Analyze Sentiment'}
        </button>
      </div>
      
      {results && (
        <div className="sentiment-results">
          <div className="insights-grid">
            <div className="insight-card">
              <h3>📊 Sentiment Score</h3>
              <div className={`sentiment-indicator sentiment-${results.sentiment}`}>
                {results.sentiment} ({Math.round(results.confidence * 100)}%)
              </div>
              <p><strong>Tone:</strong> {results.tone}</p>
            </div>
            
            <div className="insight-card">
              <h3>🎭 Emotional Indicators</h3>
              <div className="emotion-tags">
                {results.emotional_indicators.map(indicator => (
                  <span key={indicator} className="emotion-tag">
                    {indicator}
                  </span>
                ))}
              </div>
            </div>
            
            <div className="insight-card">
              <h3>💼 Business Impact</h3>
              <p>{results.business_impact}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SentimentAnalysis;
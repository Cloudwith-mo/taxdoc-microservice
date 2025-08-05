import React, { useState } from 'react';
import './ChatbotQA.css';

const ChatbotQA = ({ documentData }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [notifyEmail, setNotifyEmail] = useState('');
  const [showNotify, setShowNotify] = useState(false);

  const handleNotifySubmit = (e) => {
    e.preventDefault();
    // Store email for notification
    localStorage.setItem('chatbot_notify_email', notifyEmail);
    setShowNotify(false);
    alert('Thanks! We\'ll notify you when Chatbot Q&A is ready.');
  };

  const suggestedQuestions = [
    "What are the key financial figures in this document?",
    "Are there any compliance issues I should be aware of?",
    "What action items can you identify?",
    "Summarize the most important information",
    "What are the tax implications?"
  ];

  return (
    <div className="chatbot-qa">
      <div className="chatbot-header">
        <h3>💬 Chatbot Q&A</h3>
        <div className="feature-badge coming-soon">COMING SOON</div>
      </div>
      
      <div className="chatbot-preview">
        <div className="preview-description">
          <h4>Ask questions about your documents in natural language</h4>
          <div className="feature-list">
            <div className="feature-item">🔍 Natural language queries</div>
            <div className="feature-item">📄 Document-specific answers</div>
            <div className="feature-item">🔗 Cross-document insights</div>
            <div className="feature-item">📤 Export conversations</div>
          </div>
        </div>

        <div className="demo-chat">
          <div className="demo-message user">
            "What's the total tax withheld on this W-2?"
          </div>
          <div className="demo-message bot">
            Based on your W-2 document, the total tax withheld is $3,247.50 (Federal: $2,890.00 + State: $357.50). This represents 18.2% of your gross wages.
          </div>
        </div>

        <div className="suggested-questions">
          <h5>Try asking:</h5>
          {suggestedQuestions.map((question, index) => (
            <div key={index} className="suggested-question">
              "{question}"
            </div>
          ))}
        </div>

        <div className="notify-section">
          <button 
            className="notify-btn"
            onClick={() => setShowNotify(true)}
          >
            🔔 Notify Me When Ready
          </button>
        </div>
      </div>

      {showNotify && (
        <div className="notify-modal">
          <div className="notify-content">
            <h4>Get Notified</h4>
            <p>Be the first to know when Chatbot Q&A launches!</p>
            <form onSubmit={handleNotifySubmit}>
              <input
                type="email"
                placeholder="Enter your email"
                value={notifyEmail}
                onChange={(e) => setNotifyEmail(e.target.value)}
                required
              />
              <div className="notify-actions">
                <button type="submit">Notify Me</button>
                <button type="button" onClick={() => setShowNotify(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatbotQA;
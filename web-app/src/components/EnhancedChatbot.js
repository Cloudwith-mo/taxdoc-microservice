import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from './AuthProvider';

const EnhancedChatbot = ({ documentData }) => {
  const [messages, setMessages] = useState([
    {
      type: 'bot',
      content: 'Hi! I can help you understand your document. Ask me anything about the extracted data.',
      timestamp: new Date(),
      sentiment: 'neutral'
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [userSentiment, setUserSentiment] = useState('neutral');
  const messagesEndRef = useRef(null);
  const { user, userTier } = useAuth();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const detectSentiment = (text) => {
    // Simple client-side sentiment detection
    const positiveWords = ['good', 'great', 'excellent', 'perfect', 'amazing', 'love', 'like', 'thanks', 'thank you'];
    const negativeWords = ['bad', 'terrible', 'awful', 'hate', 'wrong', 'error', 'problem', 'issue', 'confused', 'frustrated'];
    
    const words = text.toLowerCase().split(' ');
    let positiveCount = 0;
    let negativeCount = 0;
    
    words.forEach(word => {
      if (positiveWords.some(pw => word.includes(pw))) positiveCount++;
      if (negativeWords.some(nw => word.includes(nw))) negativeCount++;
    });
    
    if (positiveCount > negativeCount) return 'positive';
    if (negativeCount > positiveCount) return 'negative';
    return 'neutral';
  };

  const getSentimentEmoji = (sentiment) => {
    switch (sentiment) {
      case 'positive': return '😊';
      case 'negative': return '😟';
      default: return '😐';
    }
  };

  const getResponseTone = (sentiment) => {
    switch (sentiment) {
      case 'positive':
        return 'enthusiastic';
      case 'negative':
        return 'empathetic';
      default:
        return 'neutral';
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const sentiment = detectSentiment(inputMessage);
    setUserSentiment(sentiment);

    const userMessage = {
      type: 'user',
      content: inputMessage,
      timestamp: new Date(),
      sentiment
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await fetch('https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('cognitoToken') || ''}`
        },
        body: JSON.stringify({
          message: inputMessage,
          document_data: documentData,
          user_sentiment: sentiment,
          response_tone: getResponseTone(sentiment),
          user_tier: userTier
        })
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();
      
      const botMessage = {
        type: 'bot',
        content: data.response,
        timestamp: new Date(),
        sentiment: data.detected_sentiment || 'neutral',
        confidence: data.sentiment_confidence
      };

      setMessages(prev => [...prev, botMessage]);

    } catch (error) {
      const errorMessage = {
        type: 'bot',
        content: sentiment === 'negative' 
          ? "I'm sorry you're having trouble. Let me try to help you better. Could you rephrase your question?"
          : "I'm having trouble processing your request right now. Please try again.",
        timestamp: new Date(),
        sentiment: 'empathetic'
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="enhanced-chatbot">
      <div className="chatbot-header">
        <h3>💬 AI Assistant</h3>
        {userTier === 'premium' && (
          <div className="sentiment-indicator">
            <span>Mood: {getSentimentEmoji(userSentiment)}</span>
          </div>
        )}
      </div>

      <div className="messages-container">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.type}`}>
            <div className="message-content">
              {message.content}
              {userTier === 'premium' && message.sentiment && (
                <div className="message-sentiment">
                  {getSentimentEmoji(message.sentiment)}
                  {message.confidence && (
                    <span className="confidence">
                      {Math.round(message.confidence * 100)}%
                    </span>
                  )}
                </div>
              )}
            </div>
            <div className="message-timestamp">
              {message.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="message bot loading">
            <div className="message-content">
              <span className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </span>
              Analyzing your question...
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <textarea
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={user ? "Ask me about your document..." : "Sign in to chat with your documents"}
          disabled={!user || isLoading}
          rows={2}
          className="chat-input"
        />
        <button
          onClick={handleSendMessage}
          disabled={!inputMessage.trim() || isLoading || !user}
          className="send-button"
        >
          {isLoading ? '⏳' : '📤'}
        </button>
      </div>

      {!user && (
        <div className="auth-prompt">
          <p>🔐 Sign in to unlock AI chat features</p>
        </div>
      )}

      {userTier === 'free' && user && (
        <div className="upgrade-prompt">
          <p>💎 Upgrade to Premium for sentiment analysis and enhanced AI responses</p>
        </div>
      )}
    </div>
  );
};

export default EnhancedChatbot;
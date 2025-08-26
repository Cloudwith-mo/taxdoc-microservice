import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './components/AuthProvider';
import AuthModal from './components/AuthModal';
import PaymentModal from './components/PaymentModal';
import EnhancedUploader from './components/EnhancedUploader';
import EnhancedResults from './components/EnhancedResults';
import EnhancedChatbot from './components/EnhancedChatbot';
import AIInsights from './components/AIInsights';
import SentimentAnalysis from './components/SentimentAnalysis';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import './styles/v2-styles.css';
import './App.css';

const AppContent = () => {
  const [results, setResults] = useState(null);
  const [activeTab, setActiveTab] = useState('process');
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const { user, userTier, logout, isAuthenticated, loading } = useAuth();

  useEffect(() => {
    // Check for payment success/failure in URL
    const urlParams = new URLSearchParams(window.location.search);
    const paymentStatus = urlParams.get('payment');
    
    if (paymentStatus === 'success') {
      // Handle successful payment
      alert('🎉 Payment successful! Your account has been upgraded.');
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (paymentStatus === 'cancelled') {
      // Handle cancelled payment
      alert('Payment was cancelled. You can try again anytime.');
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const handleResults = (newResults) => {
    setResults(newResults);
    setActiveTab('results');
  };

  const getTierBadge = () => {
    const badges = {
      free: { text: 'Free', color: 'gray', icon: '🆓' },
      premium: { text: 'Premium', color: 'gold', icon: '💎' },
      enterprise: { text: 'Enterprise', color: 'purple', icon: '🏢' }
    };
    
    const badge = badges[userTier] || badges.free;
    return (
      <span className={`tier-badge ${badge.color}`}>
        {badge.icon} {badge.text}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner">⏳</div>
        <p>Loading TaxDoc Pro...</p>
      </div>
    );
  }

  return (
    <div className="app v2">
      <header className="app-header v2">
        <div className="header-content">
          <div className="brand">
            <h1>🏛️ TaxDoc Pro v2.0</h1>
            <p>AI-Powered Document Intelligence with User Accounts & Premium Features</p>
          </div>
          
          <div className="header-actions">
            {isAuthenticated ? (
              <div className="user-menu">
                <div className="user-info">
                  <span className="user-name">👋 {user.attributes?.name || user.username}</span>
                  {getTierBadge()}
                </div>
                <div className="user-actions">
                  {userTier === 'free' && (
                    <button 
                      className="upgrade-button"
                      onClick={() => setShowPaymentModal(true)}
                    >
                      💎 Upgrade
                    </button>
                  )}
                  <button 
                    className="logout-button"
                    onClick={logout}
                  >
                    🚪 Sign Out
                  </button>
                </div>
              </div>
            ) : (
              <button 
                className="auth-button"
                onClick={() => setShowAuthModal(true)}
              >
                🔐 Sign In / Sign Up
              </button>
            )}
          </div>
        </div>

        <nav className="nav-tabs v2">
          <button 
            className={`nav-tab ${activeTab === 'process' ? 'active' : ''}`}
            onClick={() => setActiveTab('process')}
          >
            📤 Upload & Process
          </button>
          
          {results && (
            <button 
              className={`nav-tab ${activeTab === 'results' ? 'active' : ''}`}
              onClick={() => setActiveTab('results')}
            >
              📊 Results
            </button>
          )}
          
          {results && isAuthenticated && (
            <button 
              className={`nav-tab ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              💬 AI Chat
            </button>
          )}
          
          {userTier === 'premium' && (
            <>
              <button 
                className={`nav-tab ${activeTab === 'insights' ? 'active' : ''}`}
                onClick={() => setActiveTab('insights')}
              >
                🧠 AI Insights
              </button>
              <button 
                className={`nav-tab ${activeTab === 'sentiment' ? 'active' : ''}`}
                onClick={() => setActiveTab('sentiment')}
              >
                😊 Sentiment
              </button>
            </>
          )}
          
          {isAuthenticated && (
            <button 
              className={`nav-tab ${activeTab === 'analytics' ? 'active' : ''}`}
              onClick={() => setActiveTab('analytics')}
            >
              📈 Analytics
            </button>
          )}
        </nav>
      </header>

      <main className="app-content">
        {activeTab === 'process' && (
          <div className="upload-section">
            <EnhancedUploader 
              onResults={handleResults} 
              userTier={userTier}
            />
            
            <div className="feature-highlights">
              <div className="feature-grid">
                <div className="feature-card">
                  <div className="feature-icon">📱</div>
                  <h3>Photo Upload</h3>
                  <p>Drag & drop photos from your phone or camera</p>
                </div>
                <div className="feature-card">
                  <div className="feature-icon">🤖</div>
                  <h3>AI Processing</h3>
                  <p>Three-layer extraction with 87-99% accuracy</p>
                </div>
                <div className="feature-card">
                  <div className="feature-icon">💬</div>
                  <h3>AI Chat</h3>
                  <p>Ask questions about your documents</p>
                </div>
                <div className="feature-card premium">
                  <div className="feature-icon">💎</div>
                  <h3>Premium Features</h3>
                  <p>Sentiment analysis, unlimited processing, priority support</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'results' && results && (
          <EnhancedResults results={results} />
        )}

        {activeTab === 'chat' && results && isAuthenticated && (
          <EnhancedChatbot documentData={results} />
        )}

        {activeTab === 'insights' && results && userTier === 'premium' && (
          <AIInsights documentData={results} />
        )}

        {activeTab === 'sentiment' && userTier === 'premium' && (
          <SentimentAnalysis />
        )}

        {activeTab === 'analytics' && isAuthenticated && (
          <AnalyticsDashboard />
        )}
      </main>

      <AuthModal 
        isOpen={showAuthModal} 
        onClose={() => setShowAuthModal(false)} 
      />
      
      <PaymentModal 
        isOpen={showPaymentModal} 
        onClose={() => setShowPaymentModal(false)} 
      />

      {!isAuthenticated && (
        <div className="upgrade-banner">
          <div className="banner-content">
            <h3>🚀 Unlock the Full Power of TaxDoc Pro</h3>
            <p>Sign up for free to save your documents, chat with AI, and access premium features</p>
            <button 
              className="banner-cta"
              onClick={() => setShowAuthModal(true)}
            >
              Get Started Free
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const AppV2 = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default AppV2;
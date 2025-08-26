import React, { useState } from 'react';
import { useAuth } from './AuthProvider';

const AuthModal = ({ isOpen, onClose }) => {
  const [mode, setMode] = useState('login'); // 'login', 'register', 'confirm'
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    confirmationCode: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const { login, register, confirmRegistration } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (mode === 'login') {
        await login(formData.email, formData.password);
        onClose();
      } else if (mode === 'register') {
        await register(formData.email, formData.password, formData.name);
        setMode('confirm');
      } else if (mode === 'confirm') {
        await confirmRegistration(formData.email, formData.confirmationCode);
        await login(formData.email, formData.password);
        onClose();
      }
    } catch (err) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  if (!isOpen) return null;

  return (
    <div className="auth-modal-overlay" onClick={onClose}>
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
        <div className="auth-modal-header">
          <h2>
            {mode === 'login' && '🔐 Sign In'}
            {mode === 'register' && '📝 Create Account'}
            {mode === 'confirm' && '✉️ Verify Email'}
          </h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {mode === 'register' && (
            <div className="form-group">
              <label>Full Name</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
                placeholder="Enter your full name"
              />
            </div>
          )}

          {(mode === 'login' || mode === 'register') && (
            <>
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                  placeholder="Enter your email"
                />
              </div>

              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  required
                  placeholder="Enter your password"
                  minLength={8}
                />
              </div>
            </>
          )}

          {mode === 'confirm' && (
            <div className="form-group">
              <label>Confirmation Code</label>
              <input
                type="text"
                name="confirmationCode"
                value={formData.confirmationCode}
                onChange={handleInputChange}
                required
                placeholder="Enter the code from your email"
              />
              <small>Check your email for the verification code</small>
            </div>
          )}

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <button type="submit" disabled={loading} className="auth-submit-button">
            {loading ? (
              <>
                <span className="spinner">⏳</span>
                {mode === 'login' && 'Signing In...'}
                {mode === 'register' && 'Creating Account...'}
                {mode === 'confirm' && 'Verifying...'}
              </>
            ) : (
              <>
                {mode === 'login' && '🔐 Sign In'}
                {mode === 'register' && '📝 Create Account'}
                {mode === 'confirm' && '✉️ Verify Email'}
              </>
            )}
          </button>
        </form>

        <div className="auth-modal-footer">
          {mode === 'login' && (
            <p>
              Don't have an account?{' '}
              <button 
                type="button" 
                className="link-button"
                onClick={() => setMode('register')}
              >
                Sign up
              </button>
            </p>
          )}
          {mode === 'register' && (
            <p>
              Already have an account?{' '}
              <button 
                type="button" 
                className="link-button"
                onClick={() => setMode('login')}
              >
                Sign in
              </button>
            </p>
          )}
          {mode === 'confirm' && (
            <p>
              <button 
                type="button" 
                className="link-button"
                onClick={() => setMode('register')}
              >
                Back to registration
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AuthModal;
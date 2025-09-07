import React, { useState } from 'react';
import { useAuth } from './AuthProvider';

const PaymentModal = ({ isOpen, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { user, userTier, upgradeTier } = useAuth();

  const plans = [
    {
      id: 'free',
      name: 'Free Tier',
      price: '$0',
      features: [
        '5 documents per month',
        'Basic extraction',
        'Standard support'
      ],
      current: userTier === 'free'
    },
    {
      id: 'premium',
      name: 'Premium',
      price: '$29/month',
      features: [
        'Unlimited documents',
        'AI insights & sentiment analysis',
        'Priority support',
        'Excel export',
        'Chat with documents'
      ],
      current: userTier === 'premium',
      stripePrice: 'price_premium_monthly' // Replace with actual Stripe price ID
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      price: '$99/month',
      features: [
        'Everything in Premium',
        'API access',
        'Custom integrations',
        'Dedicated support',
        'SLA guarantee'
      ],
      current: userTier === 'enterprise',
      stripePrice: 'price_enterprise_monthly' // Replace with actual Stripe price ID
    }
  ];

  const handleUpgrade = async (plan) => {
    if (!user) {
      setError('Please sign in to upgrade');
      return;
    }

    if (plan.id === 'free') {
      return; // Already free
    }

    setLoading(true);
    setError('');

    try {
      // Create Stripe checkout session
      const response = await fetch('https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod/create-checkout-session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('cognitoToken')}`
        },
        body: JSON.stringify({
          price_id: plan.stripePrice,
          success_url: `${window.location.origin}?payment=success`,
          cancel_url: `${window.location.origin}?payment=cancelled`
        })
      });

      if (!response.ok) {
        throw new Error('Failed to create checkout session');
      }

      const { checkout_url } = await response.json();
      
      // Redirect to Stripe Checkout
      window.location.href = checkout_url;

    } catch (err) {
      setError(err.message || 'Payment failed');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="payment-modal-overlay" onClick={onClose}>
      <div className="payment-modal" onClick={(e) => e.stopPropagation()}>
        <div className="payment-modal-header">
          <h2>💳 Choose Your Plan</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="pricing-plans">
          {plans.map((plan) => (
            <div 
              key={plan.id} 
              className={`pricing-plan ${plan.current ? 'current' : ''} ${plan.id === 'premium' ? 'popular' : ''}`}
            >
              {plan.id === 'premium' && (
                <div className="popular-badge">Most Popular</div>
              )}
              
              <div className="plan-header">
                <h3>{plan.name}</h3>
                <div className="plan-price">{plan.price}</div>
              </div>

              <ul className="plan-features">
                {plan.features.map((feature, index) => (
                  <li key={index}>✅ {feature}</li>
                ))}
              </ul>

              <button
                onClick={() => handleUpgrade(plan)}
                disabled={loading || plan.current}
                className={`plan-button ${plan.current ? 'current' : ''}`}
              >
                {plan.current ? (
                  'Current Plan'
                ) : loading ? (
                  <>
                    <span className="spinner">⏳</span>
                    Processing...
                  </>
                ) : (
                  `Upgrade to ${plan.name}`
                )}
              </button>
            </div>
          ))}
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <div className="payment-footer">
          <p>🔒 Secure payment powered by Stripe</p>
          <p>Cancel anytime • 30-day money-back guarantee</p>
        </div>
      </div>
    </div>
  );
};

export default PaymentModal;
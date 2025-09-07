import React, { useState } from 'react';
import { createCheckoutSession } from '../services/api';

const PricingModal = ({ isOpen, onClose, userEmail }) => {
  const [loading, setLoading] = useState(false);

  const handleSubscribe = async (plan) => {
    setLoading(true);
    try {
      const result = await createCheckoutSession(plan, userEmail);
      if (result.checkout_url) {
        window.location.href = result.checkout_url;
      }
    } catch (error) {
      console.error('Payment error:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold">Choose Your Plan</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">×</button>
        </div>
        
        <div className="grid md:grid-cols-2 gap-6">
          <div className="border rounded-lg p-6">
            <h3 className="text-xl font-bold mb-2">Pro Plan</h3>
            <p className="text-3xl font-bold mb-4">$29<span className="text-sm">/month</span></p>
            <ul className="mb-6 space-y-2">
              <li>✓ 1,000 documents/month</li>
              <li>✓ AI-powered extraction</li>
              <li>✓ Batch processing</li>
              <li>✓ Export formats</li>
              <li>✓ Email support</li>
            </ul>
            <button
              onClick={() => handleSubscribe('pro')}
              disabled={loading}
              className="w-full bg-purple-600 text-white p-3 rounded hover:bg-purple-700 disabled:opacity-50"
            >
              {loading ? 'Processing...' : 'Subscribe to Pro'}
            </button>
          </div>
          
          <div className="border rounded-lg p-6 border-purple-500">
            <h3 className="text-xl font-bold mb-2">Enterprise</h3>
            <p className="text-3xl font-bold mb-4">$99<span className="text-sm">/month</span></p>
            <ul className="mb-6 space-y-2">
              <li>✓ Unlimited documents</li>
              <li>✓ Custom AI models</li>
              <li>✓ API access</li>
              <li>✓ Priority support</li>
              <li>✓ Custom integrations</li>
            </ul>
            <button
              onClick={() => handleSubscribe('enterprise')}
              disabled={loading}
              className="w-full bg-purple-600 text-white p-3 rounded hover:bg-purple-700 disabled:opacity-50"
            >
              {loading ? 'Processing...' : 'Subscribe to Enterprise'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PricingModal;
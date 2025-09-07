const API_BASE = 'https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod';

// SNS Alerts API
export const subscribeToAlerts = async (email, alertTypes) => {
  const response = await fetch(`${API_BASE}/sns/subscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, alert_types: alertTypes })
  });
  return response.json();
};

export const getAlertPreferences = async (userId) => {
  const response = await fetch(`${API_BASE}/sns/preferences?user_id=${userId}`);
  return response.json();
};

// Enhanced Analytics API
export const getAnalytics = async (timeRange = '7d') => {
  const response = await fetch(`${API_BASE}/analytics?range=${timeRange}`);
  return response.json();
};

export const getProcessingMetrics = async () => {
  const response = await fetch(`${API_BASE}/analytics/metrics`);
  return response.json();
};

// Batch Status Tracking API
export const getBatchStatus = async (batchId) => {
  const response = await fetch(`${API_BASE}/batch/status/${batchId}`);
  return response.json();
};

export const getAllBatches = async (userId) => {
  const response = await fetch(`${API_BASE}/batch/list?user_id=${userId}`);
  return response.json();
};

// Stripe Payment API
export const createCheckoutSession = async (plan, email) => {
  const response = await fetch(`${API_BASE}/stripe/create-checkout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      plan,
      email,
      amount: plan === 'pro' ? 2900 : 9900,
      success_url: `${window.location.origin}/success`,
      cancel_url: `${window.location.origin}/pricing`
    })
  });
  return response.json();
};

export const getSubscriptionStatus = async (customerId) => {
  const response = await fetch(`${API_BASE}/stripe/subscription-status?customer_id=${customerId}`);
  return response.json();
};

// Cognito Auth API
export const registerUser = async (email, password) => {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  return response.json();
};

export const loginUser = async (email, password) => {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  return response.json();
};

export const refreshToken = async (refreshToken, username) => {
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken, username })
  });
  return response.json();
};
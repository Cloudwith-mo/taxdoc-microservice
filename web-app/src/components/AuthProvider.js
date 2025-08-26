import React, { createContext, useContext, useState, useEffect } from 'react';
import { Amplify } from 'aws-amplify';
import { signUp, signIn, signOut, getCurrentUser, confirmSignUp } from 'aws-amplify/auth';

// Configure Amplify (you'll need to update these with your actual Cognito settings)
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: process.env.REACT_APP_USER_POOL_ID || 'us-east-1_XXXXXXXXX',
      userPoolClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID || 'XXXXXXXXXXXXXXXXXXXXXXXXXX',
      region: 'us-east-1'
    }
  }
});

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [userTier, setUserTier] = useState('free');

  useEffect(() => {
    checkAuthState();
  }, []);

  const checkAuthState = async () => {
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      
      // Get user tier from attributes or API
      const tier = currentUser.attributes?.['custom:tier'] || 'free';
      setUserTier(tier);
      
      // Store token for API calls
      const session = await currentUser.getSession();
      localStorage.setItem('cognitoToken', session.getIdToken().getJwtToken());
    } catch (error) {
      setUser(null);
      localStorage.removeItem('cognitoToken');
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      const result = await signIn({ username: email, password });
      await checkAuthState();
      return result;
    } catch (error) {
      throw error;
    }
  };

  const register = async (email, password, name) => {
    try {
      const result = await signUp({
        username: email,
        password,
        attributes: {
          email,
          name,
          'custom:tier': 'free'
        }
      });
      return result;
    } catch (error) {
      throw error;
    }
  };

  const confirmRegistration = async (email, code) => {
    try {
      await confirmSignUp({ username: email, confirmationCode: code });
      return true;
    } catch (error) {
      throw error;
    }
  };

  const logout = async () => {
    try {
      await signOut();
      setUser(null);
      setUserTier('free');
      localStorage.removeItem('cognitoToken');
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const upgradeTier = (newTier) => {
    setUserTier(newTier);
    // Update user attributes in Cognito
    // This would typically be done via an API call after successful payment
  };

  const value = {
    user,
    userTier,
    loading,
    login,
    register,
    confirmRegistration,
    logout,
    upgradeTier,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
import React, { useEffect, useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import APIService from '../../services/api';

const GoogleCallback = () => {
  const [status, setStatus] = useState('processing');
  const [error, setError] = useState('');
  const { checkAuthStatus } = useAuth();

  useEffect(() => {
    const handleCallback = async () => {
      // Check URL parameters for success/error from backend redirect
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get('token');
      const authError = urlParams.get('error');

      if (authError) {
        setError(`Authentication failed: ${authError}`);
        setStatus('error');
        return;
      }

      if (token) {
        // Store the token from the URL parameter
        localStorage.setItem('access_token', token);
        localStorage.setItem('token_type', 'bearer');
        
        // Fetch user data to ensure we have the latest info (including is_superuser)
        try {
          await checkAuthStatus();
        } catch (err) {
          console.error('Error fetching user data after OAuth:', err);
        }
        
        setStatus('success');
        
        // Redirect to main app after a brief delay
        setTimeout(() => {
          window.location.href = '/';
        }, 2000);
      } else {
        setError('No authentication token received');
        setStatus('error');
      }
    };

    handleCallback();
  }, [checkAuthStatus]);

  if (status === 'processing') {
    return (
      <div className="oauth-callback">
        <div className="callback-content">
          <div className="spinner"></div>
          <h2>Completing Google Sign-In...</h2>
          <p>Please wait while we finish setting up your account.</p>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="oauth-callback">
        <div className="callback-content error">
          <h2>Sign-In Failed</h2>
          <p>{error}</p>
          <button 
            className="btn-primary"
            onClick={() => window.location.href = '/'}
          >
            Return to Home
          </button>
        </div>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="oauth-callback">
        <div className="callback-content success">
          <div className="success-icon">✅</div>
          <h2>Welcome!</h2>
          <p>You've successfully signed in with Google.</p>
          <p>Redirecting to your dashboard...</p>
        </div>
      </div>
    );
  }

  return null;
};

export default GoogleCallback;

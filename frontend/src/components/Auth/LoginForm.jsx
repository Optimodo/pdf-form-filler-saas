import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import APIService from '../../services/api';

const LoginForm = ({ onSwitchToRegister, onClose }) => {
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    // Clear error when user starts typing
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(formData.email, formData.password);
    
    if (result.success) {
      onClose();
    } else {
      setError(result.error);
    }
    
    setLoading(false);
  };

  const handleGoogleLogin = async () => {
    try {
      // Get the authorization URL from the API
      const response = await fetch(APIService.getGoogleOAuthUrl());
      const data = await response.json();
      
      // Redirect to the Google authorization URL
      if (data.authorization_url) {
        window.location.href = data.authorization_url;
      } else {
        setError('Failed to get Google authorization URL');
      }
    } catch (error) {
      console.error('Google OAuth Error:', error);
      setError('Failed to initiate Google login');
    }
  };

  return (
    <div className="login-form">
      <div className="auth-header">
        <h2>Welcome Back</h2>
        <p>Sign in to your PDF Form Filler account</p>
      </div>

      {/* Social Login Buttons */}
      <div className="social-login-section">
        <button 
          type="button" 
          className="btn-social btn-google"
          onClick={handleGoogleLogin}
        >
          <span className="social-icon">🔍</span>
          Continue with Google
        </button>
        
        {/* Placeholder for Apple Login */}
        <button 
          type="button" 
          className="btn-social btn-apple"
          disabled
          title="Apple Sign-In coming soon"
        >
          <span className="social-icon">🍎</span>
          Sign in with Apple
          <span className="coming-soon">(Soon)</span>
        </button>
      </div>

      <div className="divider">
        <span>or continue with email</span>
      </div>

      {/* Email/Password Login Form */}
      <form onSubmit={handleSubmit} className="auth-form">
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <div className="form-group">
          <label htmlFor="email">Email Address</label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
            placeholder="Enter your email"
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            required
            placeholder="Enter your password"
            disabled={loading}
          />
        </div>

        <button 
          type="submit" 
          className="btn-primary btn-auth"
          disabled={loading}
        >
          {loading ? 'Signing In...' : 'Sign In'}
        </button>
      </form>

      <div className="auth-footer">
        <p>
          Don't have an account?{' '}
          <button 
            type="button" 
            className="link-button"
            onClick={onSwitchToRegister}
          >
            Sign up here
          </button>
        </p>
        
        <button type="button" className="link-button forgot-password">
          Forgot your password?
        </button>
      </div>
    </div>
  );
};

export default LoginForm;

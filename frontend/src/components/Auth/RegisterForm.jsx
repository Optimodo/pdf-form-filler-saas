import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import APIService from '../../services/api';

const RegisterForm = ({ onSwitchToLogin, onClose }) => {
  const { register } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

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

    // Validate password confirmation
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    // Validate password strength
    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters long');
      setLoading(false);
      return;
    }

    const registrationData = {
      email: formData.email,
      password: formData.password,
      first_name: formData.first_name || null,
      last_name: formData.last_name || null,
    };

    const result = await register(registrationData);
    
    if (result.success) {
      setSuccess(true);
    } else {
      setError(result.error);
    }
    
    setLoading(false);
  };

  const handleGoogleLogin = () => {
    // Redirect to Google OAuth
    window.location.href = APIService.getGoogleOAuthUrl();
  };

  if (success) {
    return (
      <div className="register-success">
        <div className="success-icon">✅</div>
        <h2>Account Created!</h2>
        <p>Your account has been successfully created.</p>
        <button 
          className="btn-primary btn-auth"
          onClick={onSwitchToLogin}
        >
          Sign In Now
        </button>
      </div>
    );
  }

  return (
    <div className="register-form">
      <div className="auth-header">
        <h2>Create Account</h2>
        <p>Start filling PDFs with your free account</p>
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
          Sign up with Apple
          <span className="coming-soon">(Soon)</span>
        </button>
      </div>

      <div className="divider">
        <span>or create account with email</span>
      </div>

      {/* Registration Form */}
      <form onSubmit={handleSubmit} className="auth-form">
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="first_name">First Name</label>
            <input
              type="text"
              id="first_name"
              name="first_name"
              value={formData.first_name}
              onChange={handleChange}
              placeholder="First name"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="last_name">Last Name</label>
            <input
              type="text"
              id="last_name"
              name="last_name"
              value={formData.last_name}
              onChange={handleChange}
              placeholder="Last name"
              disabled={loading}
            />
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="email">Email Address *</label>
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
          <label htmlFor="password">Password *</label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            required
            placeholder="Create a password (min. 6 characters)"
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="confirmPassword">Confirm Password *</label>
          <input
            type="password"
            id="confirmPassword"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            required
            placeholder="Confirm your password"
            disabled={loading}
          />
        </div>

        <div className="form-info">
          <p>🎉 <strong>Free tier includes:</strong> 10 PDF generations per month</p>
        </div>

        <button 
          type="submit" 
          className="btn-primary btn-auth"
          disabled={loading}
        >
          {loading ? 'Creating Account...' : 'Create Account'}
        </button>
      </form>

      <div className="auth-footer">
        <p>
          Already have an account?{' '}
          <button 
            type="button" 
            className="link-button"
            onClick={onSwitchToLogin}
          >
            Sign in here
          </button>
        </p>
      </div>
    </div>
  );
};

export default RegisterForm;

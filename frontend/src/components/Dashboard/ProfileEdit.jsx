import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import APIService from '../../services/api';

const ProfileEdit = () => {
  const { user, isAuthenticated, loadUser } = useAuth();
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: ''
  });
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [activeSection, setActiveSection] = useState('profile');

  // Helper to detect if user is OAuth-only (likely doesn't have a password)
  const isOAuthUser = user && user.email && !user.first_name && !user.last_name;

  useEffect(() => {
    if (user) {
      setFormData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        email: user.email || ''
      });
    }
  }, [user]);


  const handleBack = () => {
    window.history.pushState({}, '', '/dashboard');
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  const handleHome = () => {
    window.history.pushState({}, '', '/');
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({
      ...prev,
      [name]: value
    }));
  };


  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: '', text: '' });

    try {
      await APIService.updateProfile(formData);
      await loadUser(); // Refresh user data
      setMessage({ type: 'success', text: 'Profile updated successfully!' });
    } catch (error) {
      setMessage({ type: 'error', text: error.message || 'Failed to update profile' });
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setMessage({ type: '', text: '' });

    if (passwordData.new_password !== passwordData.confirm_password) {
      setMessage({ type: 'error', text: 'New passwords do not match' });
      return;
    }

    if (passwordData.new_password.length < 8) {
      setMessage({ type: 'error', text: 'New password must be at least 8 characters long' });
      return;
    }

    setLoading(true);

    try {
      // Use FastAPI-Users' built-in user update endpoint for password changes
      await APIService.changePassword({
        current_password: passwordData.current_password,
        new_password: passwordData.new_password
      });
      setPasswordData({
        current_password: '',
        new_password: '',
        confirm_password: ''
      });
      setMessage({ 
        type: 'success', 
        text: isOAuthUser ? 'Password set successfully! You can now sign in with email/password.' : 'Password updated successfully!' 
      });
    } catch (error) {
      setMessage({ type: 'error', text: error.message || 'Failed to update password' });
    } finally {
      setLoading(false);
    }
  };

  if (!isAuthenticated || !user) {
    return (
      <div className="profile-container">
        <div className="profile-error">
          <h2>Access Denied</h2>
          <p>Please sign in to edit your profile.</p>
          <button className="btn-primary" onClick={handleHome}>
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-container">
      <div className="profile-header">
        <div className="profile-title">
          <button className="back-btn" onClick={handleBack} title="Back to Dashboard">
            ←
          </button>
          <h1>Account Settings</h1>
        </div>
      </div>

      <div className="profile-tabs">
        <button 
          className={`tab-btn ${activeSection === 'profile' ? 'active' : ''}`}
          onClick={() => setActiveSection('profile')}
        >
          Profile Information
        </button>
        <button 
          className={`tab-btn ${activeSection === 'password' ? 'active' : ''}`}
          onClick={() => setActiveSection('password')}
        >
          Change Password
        </button>
      </div>

      {message.text && (
        <div className={`message ${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="profile-content">
        {activeSection === 'profile' && (
          <div className="profile-section">
            <div className="section-card">
              <div className="card-header">
                <h3>👤 Personal Information</h3>
                <p>Update your personal details</p>
              </div>
              
              <form onSubmit={handleProfileSubmit} className="profile-form">
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="first_name">First Name</label>
                    <input
                      type="text"
                      id="first_name"
                      name="first_name"
                      value={formData.first_name}
                      onChange={handleInputChange}
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
                      onChange={handleInputChange}
                      disabled={loading}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="email">Email Address</label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    disabled={loading}
                    required
                  />
                </div>

                <div className="form-actions">
                  <button 
                    type="submit" 
                    className="btn-primary"
                    disabled={loading}
                  >
                    {loading ? 'Updating...' : 'Save Changes'}
                  </button>
                  <button 
                    type="button" 
                    className="btn-secondary"
                    onClick={handleBack}
                    disabled={loading}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {activeSection === 'password' && (
          <div className="profile-section">
            <div className="section-card">
              <div className="card-header">
                <h3>🔐 {isOAuthUser ? 'Set Password' : 'Change Password'}</h3>
                <p>
                  {isOAuthUser 
                    ? 'Set a password to enable email/password login'
                    : 'Update your account password'
                  }
                </p>
              </div>

              {isOAuthUser && (
                <div className="oauth-info">
                  <p>
                    <strong>🔵 You signed in with Google</strong>
                  </p>
                  <p>
                    Setting a password will allow you to sign in with your email and password 
                    in addition to Google. This provides a backup login method and enhanced security.
                  </p>
                </div>
              )}
              
              <form onSubmit={handlePasswordSubmit} className="profile-form">
                <div className="form-group">
                  <label htmlFor="new_password">New Password</label>
                  <input
                    type="password"
                    id="new_password"
                    name="new_password"
                    value={passwordData.new_password}
                    onChange={handlePasswordChange}
                    disabled={loading}
                    required
                    minLength="8"
                  />
                  <small className="form-help">Must be at least 8 characters long</small>
                </div>

                <div className="form-group">
                  <label htmlFor="confirm_password">Confirm New Password</label>
                  <input
                    type="password"
                    id="confirm_password"
                    name="confirm_password"
                    value={passwordData.confirm_password}
                    onChange={handlePasswordChange}
                    disabled={loading}
                    required
                    minLength="8"
                  />
                </div>

                <div className="form-actions">
                  <button 
                    type="submit" 
                    className="btn-primary"
                    disabled={loading}
                  >
                    {loading ? (isOAuthUser ? 'Setting...' : 'Updating...') : (isOAuthUser ? 'Set Password' : 'Update Password')}
                  </button>
                  <button 
                    type="button" 
                    className="btn-secondary"
                    onClick={handleBack}
                    disabled={loading}
                  >
                    Cancel
                  </button>
                </div>
              </form>

              <div className="password-info">
                <h4>{isOAuthUser ? 'Password Requirements:' : 'Password Requirements:'}</h4>
                <ul>
                  <li>At least 8 characters long</li>
                  <li>We recommend using a mix of letters, numbers, and symbols</li>
                  {isOAuthUser ? (
                    <>
                      <li>Your Google login will still work after setting a password</li>
                      <li>You'll have two ways to sign in: Google or email/password</li>
                    </>
                  ) : (
                    <li>This will replace your current password</li>
                  )}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProfileEdit;

import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import AuthModal from '../Auth/AuthModal';

const UserInfo = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState('login');
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef(null);

  const handleLogin = () => {
    setAuthMode('login');
    setShowAuthModal(true);
  };

  const handleRegister = () => {
    setAuthMode('register');
    setShowAuthModal(true);
  };

  const handleLogout = async () => {
    await logout();
    setShowDropdown(false);
  };

  const handleDashboard = () => {
    window.history.pushState({}, '', '/dashboard');
    window.dispatchEvent(new PopStateEvent('popstate'));
    setShowDropdown(false);
  };

  const handleAdmin = () => {
    window.history.pushState({}, '', '/admin');
    window.dispatchEvent(new PopStateEvent('popstate'));
    setShowDropdown(false);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  if (isAuthenticated && user) {
    // Authenticated user display
    const displayName = user.first_name 
      ? `${user.first_name} ${user.last_name || ''}`.trim()
      : user.email.split('@')[0];
    
    const planDisplay = user.subscription_tier === 'free' ? 'Free' : user.subscription_tier;

    return (
      <div className="user-info authenticated" ref={dropdownRef}>
        <div 
          className="user-display"
          onClick={() => setShowDropdown(!showDropdown)}
        >
          <span className="user-avatar">👤</span>
          <span className="user-details">
            {displayName} | {planDisplay}
          </span>
          <span className="dropdown-arrow">{showDropdown ? '▲' : '▼'}</span>
        </div>
        
        {showDropdown && (
          <div className="user-dropdown">
            <div className="dropdown-section">
              <div className="dropdown-header">
                <strong>{displayName}</strong>
                <div className="user-tier">{planDisplay} Plan</div>
                <div className="user-credits">{user.credits_remaining || 0} credits remaining</div>
              </div>
            </div>
            
            <div className="dropdown-divider"></div>
            
            <div className="dropdown-section">
              <button className="dropdown-item" onClick={handleDashboard}>
                <span className="dropdown-icon">📊</span>
                Dashboard
              </button>
              {user.is_superuser && (
                <button className="dropdown-item admin-item" onClick={handleAdmin}>
                  <span className="dropdown-icon">⚙️</span>
                  Admin Panel
                </button>
              )}
              <button className="dropdown-item" onClick={handleLogout}>
                <span className="dropdown-icon">↗️</span>
                Sign Out
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Unauthenticated user display
  return (
    <>
      <div className="user-info unauthenticated">
        <button 
          className="auth-btn login-btn"
          onClick={handleLogin}
        >
          Sign In
        </button>
        <button 
          className="auth-btn register-btn"
          onClick={handleRegister}
        >
          Sign Up
        </button>
      </div>
      
      <AuthModal 
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        initialMode={authMode}
      />
    </>
  );
};

export default UserInfo;

import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import AuthModal from '../Auth/AuthModal';

const UserInfo = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState('login');

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
  };

  if (isAuthenticated && user) {
    // Authenticated user display
    const displayName = user.first_name 
      ? `${user.first_name} ${user.last_name || ''}`.trim()
      : user.email.split('@')[0];
    
    const planDisplay = user.subscription_tier === 'free' ? 'Free' : user.subscription_tier;

    return (
      <div className="user-info authenticated">
        <span className="user-avatar">👤</span>
        <span className="user-details">
          {displayName} | {planDisplay} | {user.credits_remaining} credits
        </span>
        <button 
          className="logout-btn"
          onClick={handleLogout}
          title="Logout"
        >
          ↗️
        </button>
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

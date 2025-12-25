import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import ProcessingHistory from './ProcessingHistory';

const UserDashboard = () => {
  const { user, isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');

  const handleBack = () => {
    window.history.pushState({}, '', '/');
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  const handleProfileEdit = () => {
    window.history.pushState({}, '', '/profile');
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  if (!isAuthenticated || !user) {
    return (
      <div className="dashboard-container">
        <div className="dashboard-error">
          <h2>Access Denied</h2>
          <p>Please sign in to access your dashboard.</p>
          <button className="btn-primary" onClick={handleBack}>
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  const displayName = user.first_name 
    ? `${user.first_name} ${user.last_name || ''}`.trim()
    : user.email.split('@')[0];

  const planDisplay = user.subscription_tier === 'free' ? 'Free' : user.subscription_tier;

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div className="dashboard-title">
          <button className="back-btn" onClick={handleBack} title="Back to Home">
            ←
          </button>
          <h1>Dashboard</h1>
        </div>
        <button className="btn-secondary" onClick={handleProfileEdit}>
          Edit Profile
        </button>
      </div>

      <div className="dashboard-tabs">
        <button 
          className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button 
          className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          Processing History
        </button>
      </div>

      <div className="dashboard-content">
        {activeTab === 'overview' && (
          <div className="tab-content">
            <div className="dashboard-grid">
              {/* User Info Card */}
              <div className="dashboard-card">
                <div className="card-header">
                  <h3>👤 Account Information</h3>
                </div>
                <div className="card-content">
                  <div className="info-row">
                    <span className="info-label">Name:</span>
                    <span className="info-value">{displayName}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Email:</span>
                    <span className="info-value">{user.email}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Plan:</span>
                    <span className="info-value plan-badge">{planDisplay}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Member Since:</span>
                    <span className="info-value">
                      {new Date(user.created_at || Date.now()).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Usage Stats Card */}
              <div className="dashboard-card">
                <div className="card-header">
                  <h3>📊 Usage Statistics</h3>
                </div>
                <div className="card-content">
                  <div className="stat-item">
                    <div className="stat-value">{user.credits_remaining || 0}</div>
                    <div className="stat-label">Credits Remaining</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value">0</div>
                    <div className="stat-label">PDFs Processed Today</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-value">0</div>
                    <div className="stat-label">Total PDFs Processed</div>
                  </div>
                </div>
              </div>

              {/* Quick Actions Card */}
              <div className="dashboard-card">
                <div className="card-header">
                  <h3>⚡ Quick Actions</h3>
                </div>
                <div className="card-content">
                  <button className="action-btn" onClick={handleBack}>
                    <span className="action-icon">📄</span>
                    <div>
                      <div className="action-title">Process PDFs</div>
                      <div className="action-desc">Upload files and generate PDFs</div>
                    </div>
                  </button>
                  <button className="action-btn" onClick={handleProfileEdit}>
                    <span className="action-icon">⚙️</span>
                    <div>
                      <div className="action-title">Account Settings</div>
                      <div className="action-desc">Manage your profile and preferences</div>
                    </div>
                  </button>
                  <button className="action-btn" disabled>
                    <span className="action-icon">💳</span>
                    <div>
                      <div className="action-title">Upgrade Plan</div>
                      <div className="action-desc">Coming soon - unlock more features</div>
                    </div>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="tab-content">
            <ProcessingHistory />
          </div>
        )}
      </div>
    </div>
  );
};

export default UserDashboard;

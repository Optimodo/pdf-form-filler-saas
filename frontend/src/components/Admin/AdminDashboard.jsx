import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import APIService from '../../services/api';
import './AdminDashboard.css';

function AdminDashboard() {
  const { user, isAuthenticated } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Check if user is authenticated and is a superuser
    if (!isAuthenticated || !user) {
      setError('You must be logged in to access the admin panel.');
      setLoading(false);
      return;
    }

    if (!user.is_superuser) {
      setError('Access denied. Admin privileges required.');
      setLoading(false);
      return;
    }

    loadDashboardStats();
  }, [isAuthenticated, user]);

  const loadDashboardStats = async () => {
    try {
      setLoading(true);
      const data = await APIService.getAdminDashboardStats();
      setStats(data);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load dashboard statistics');
      console.error('Dashboard stats error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="admin-dashboard">
        <div className="loading">Loading admin dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-dashboard">
        <h1>Admin Dashboard</h1>
        <div className="error-message">Error: {error}</div>
        {error.includes('Access denied') || error.includes('must be logged in') ? (
          <button
            onClick={() => {
              window.location.pathname = '/';
            }}
            className="btn-primary"
          >
            Return to Home
          </button>
        ) : (
          <button onClick={loadDashboardStats} className="btn-primary">Retry</button>
        )}
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="admin-dashboard">
        <div className="error-message">No data available</div>
      </div>
    );
  }

  return (
    <div className="admin-dashboard">
      <h1>Admin Dashboard</h1>
      
      <div className="stats-grid">
        {/* Users Section */}
        <div className="stat-card">
          <h2>Users</h2>
          <div className="stat-value">{stats.users?.total || 0}</div>
          <div className="stat-label">Total Users</div>
          <div className="stat-details">
            <div>Active (30d): {stats.users?.active || 0}</div>
            <div className="tier-breakdown">
              {stats.users?.by_tier && Object.entries(stats.users.by_tier).map(([tier, count]) => (
                <span key={tier} className="tier-badge">{tier}: {count}</span>
              ))}
            </div>
          </div>
        </div>

        {/* Jobs Section */}
        <div className="stat-card">
          <h2>Processing Jobs</h2>
          <div className="stat-value">{stats.jobs?.total || 0}</div>
          <div className="stat-label">Total Jobs</div>
          <div className="stat-details">
            <div>Successful: {stats.jobs?.successful || 0}</div>
            <div>Last 24h: {stats.jobs?.recent_24h || 0}</div>
          </div>
        </div>

        {/* Processing Section */}
        <div className="stat-card">
          <h2>PDFs Processed</h2>
          <div className="stat-value">{stats.processing?.total_pdfs || 0}</div>
          <div className="stat-label">Total PDFs Generated</div>
        </div>

        {/* Storage Section */}
        <div className="stat-card">
          <h2>Storage</h2>
          <div className="stat-value">{stats.storage?.total_display || '0 bytes'}</div>
          <div className="stat-label">Total Storage Used</div>
        </div>
      </div>

      <div className="dashboard-actions">
        <button
          onClick={() => {
            window.location.pathname = '/admin/users';
          }}
          className="btn-primary"
        >
          Manage Users
        </button>
        <button
          onClick={() => {
            window.location.pathname = '/admin/tiers';
          }}
          className="btn-primary"
        >
          Manage Subscription Tiers
        </button>
      </div>
    </div>
  );
}

export default AdminDashboard;


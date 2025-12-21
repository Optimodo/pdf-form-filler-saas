import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import APIService from '../../services/api';
import './AdminActivityLogs.css';

function AdminActivityLogs() {
  const { user, isAuthenticated } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(0);
  const [limit] = useState(100);
  const [skip, setSkip] = useState(0);
  const [categoryFilter, setCategoryFilter] = useState('');
  const [activityTypeFilter, setActivityTypeFilter] = useState('');

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

    loadActivityLogs();
  }, [isAuthenticated, user, skip, categoryFilter, activityTypeFilter]);

  const loadActivityLogs = async () => {
    try {
      setLoading(true);
      const category = categoryFilter || null;
      const activityType = activityTypeFilter || null;
      const data = await APIService.getSystemActivityLogs(category, activityType, limit, skip);
      setLogs(data.logs || []);
      setTotal(data.total || 0);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load activity logs');
      console.error('Activity logs error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCategoryFilterChange = (e) => {
    setCategoryFilter(e.target.value);
    setSkip(0); // Reset pagination when filter changes
  };

  const handleActivityTypeFilterChange = (e) => {
    setActivityTypeFilter(e.target.value);
    setSkip(0); // Reset pagination when filter changes
  };

  const handlePreviousPage = () => {
    if (skip > 0) {
      setSkip(Math.max(0, skip - limit));
    }
  };

  const handleNextPage = () => {
    if (skip + limit < total) {
      setSkip(skip + limit);
    }
  };

  const formatChanges = (changes) => {
    if (!changes) return null;
    if (typeof changes === 'string') {
      try {
        changes = JSON.parse(changes);
      } catch (e) {
        return changes;
      }
    }
    return JSON.stringify(changes, null, 2);
  };

  if (loading && logs.length === 0) {
    return (
      <div className="admin-activity-logs">
        <div className="loading">Loading activity logs...</div>
      </div>
    );
  }

  if (error && logs.length === 0) {
    return (
      <div className="admin-activity-logs">
        <h1>System Activity Logs</h1>
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
          <button onClick={loadActivityLogs} className="btn-primary">Retry</button>
        )}
      </div>
    );
  }

  return (
    <div className="admin-activity-logs">
      <div className="header-section">
        <h1>System Activity Logs</h1>
        <button
          onClick={() => {
            window.location.pathname = '/admin';
          }}
          className="btn-secondary"
        >
          ← Back to Dashboard
        </button>
      </div>

      <div className="filters-section">
        <div className="filter-group">
          <label htmlFor="category-filter">Category:</label>
          <select
            id="category-filter"
            value={categoryFilter}
            onChange={handleCategoryFilterChange}
            className="filter-select"
          >
            <option value="">All Categories</option>
            <option value="admin">Admin</option>
            <option value="system">System</option>
            <option value="user">User</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="activity-type-filter">Activity Type:</label>
          <select
            id="activity-type-filter"
            value={activityTypeFilter}
            onChange={handleActivityTypeFilterChange}
            className="filter-select"
          >
            <option value="">All Types</option>
            <option value="tier_updated">Tier Updated</option>
            <option value="admin_action">Admin Action</option>
            <option value="system_event">System Event</option>
          </select>
        </div>
      </div>

      {loading && logs.length > 0 && (
        <div className="loading-overlay">Refreshing...</div>
      )}

      <div className="logs-summary">
        Showing {logs.length} of {total} logs
      </div>

      {logs.length === 0 ? (
        <div className="no-logs">No activity logs found</div>
      ) : (
        <>
          <div className="logs-list">
            {logs.map(log => (
              <div key={log.id} className="log-item">
                <div className="log-header">
                  <span className={`log-category log-category-${log.category}`}>
                    {log.category}
                  </span>
                  <span className="log-type">{log.activity_type.replace(/_/g, ' ')}</span>
                  <span className="log-date">{new Date(log.created_at).toLocaleString()}</span>
                </div>
                <div className="log-action">{log.action}</div>
                {log.description && (
                  <div className="log-description">{log.description}</div>
                )}
                {log.actor && (
                  <div className="log-actor">
                    <strong>Performed by:</strong> {log.actor.email}
                    {log.actor.first_name && ` (${log.actor.first_name} ${log.actor.last_name || ''})`}
                  </div>
                )}
                {log.reason && (
                  <div className="log-reason">
                    <strong>Reason:</strong> {log.reason}
                  </div>
                )}
                {log.changes && (
                  <div className="log-changes">
                    <strong>Changes:</strong>
                    <pre>{formatChanges(log.changes)}</pre>
                  </div>
                )}
                {log.related_tier_id && (
                  <div className="log-related">
                    <strong>Related Tier ID:</strong> {log.related_tier_id}
                  </div>
                )}
                <div className="log-metadata">
                  {log.ip_address && <span>IP: {log.ip_address}</span>}
                  {log.country && <span>Country: {log.country}</span>}
                  {log.actor_type && <span>Actor Type: {log.actor_type}</span>}
                </div>
              </div>
            ))}
          </div>

          <div className="pagination">
            <button
              onClick={handlePreviousPage}
              disabled={skip === 0}
              className="btn-secondary"
            >
              Previous
            </button>
            <span className="pagination-info">
              Page {Math.floor(skip / limit) + 1} of {Math.ceil(total / limit)}
            </span>
            <button
              onClick={handleNextPage}
              disabled={skip + limit >= total}
              className="btn-secondary"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default AdminActivityLogs;


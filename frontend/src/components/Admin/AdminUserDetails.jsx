import React, { useState, useEffect } from 'react';
import APIService from '../../services/api';
import './AdminUserDetails.css';

function AdminUserDetails() {
  // Extract userId from URL path (format: /admin/users/{userId})
  const pathParts = window.location.pathname.split('/');
  const userId = pathParts[pathParts.length - 1];
  const [userData, setUserData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [editingLimits, setEditingLimits] = useState(false);
  const [limitValues, setLimitValues] = useState({});

  useEffect(() => {
    if (userId) {
      loadUserDetails();
    }
  }, [userId]);

  const loadUserDetails = async () => {
    try {
      setLoading(true);
      const data = await APIService.getUserDetails(userId);
      setUserData(data);
      
      // Initialize limit values for editing (store MB values for file sizes)
      if (data.limits && data.limits.current_limits) {
        const limits = data.limits.current_limits;
        const pdfBytes = parseFileSize(limits.max_pdf_size);
        const csvBytes = parseFileSize(limits.max_csv_size);
        setLimitValues({
          max_pdf_size: parseFloat(bytesToMb(pdfBytes)),
          max_csv_size: parseFloat(bytesToMb(csvBytes)),
          max_daily_jobs: limits.max_daily_jobs,
          max_monthly_jobs: limits.max_monthly_jobs,
          max_files_per_job: limits.max_files_per_job,
          can_save_templates: limits.can_save_templates,
          can_use_api: limits.can_use_api,
        });
      }
      
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load user details');
      console.error('User details error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Helper to parse file size from display format (e.g., "100.0 MB") to bytes
  const parseFileSize = (sizeStr) => {
    if (typeof sizeStr === 'number') return sizeStr;
    if (!sizeStr || typeof sizeStr !== 'string') return 0;
    
    const match = sizeStr.match(/^([\d.]+)\s*(KB|MB|GB|bytes?)$/i);
    if (!match) return 0;
    
    const value = parseFloat(match[1]);
    const unit = match[2].toUpperCase();
    
    const multipliers = {
      'BYTES': 1,
      'BYTE': 1,
      'KB': 1024,
      'MB': 1024 * 1024,
      'GB': 1024 * 1024 * 1024,
    };
    
    return Math.round(value * (multipliers[unit] || 1));
  };

  // Helper to format bytes to display format
  const formatFileSize = (bytes) => {
    if (bytes >= 1024 * 1024 * 1024) {
      return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
    } else if (bytes >= 1024 * 1024) {
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    } else if (bytes >= 1024) {
      return (bytes / 1024).toFixed(1) + ' KB';
    }
    return bytes + ' bytes';
  };

  // Helper to convert MB input to bytes
  const mbToBytes = (mb) => Math.round(mb * 1024 * 1024);

  // Helper to convert bytes to MB for input
  const bytesToMb = (bytes) => (bytes / (1024 * 1024)).toFixed(1);

  const handleSaveLimits = async () => {
    if (!window.confirm('Save these custom limits? This will override the subscription tier limits.')) return;

    try {
      setActionLoading(true);
      
      // Convert MB values to bytes for file sizes
      const customLimits = {
        max_pdf_size: mbToBytes(limitValues.max_pdf_size),
        max_csv_size: mbToBytes(limitValues.max_csv_size),
        max_daily_jobs: parseInt(limitValues.max_daily_jobs),
        max_monthly_jobs: parseInt(limitValues.max_monthly_jobs),
        max_files_per_job: parseInt(limitValues.max_files_per_job),
        can_save_templates: limitValues.can_save_templates,
        can_use_api: limitValues.can_use_api,
      };

      const reason = window.prompt('Reason for custom limits (optional):') || 'Admin override';
      
      await APIService.setUserCustomLimits(userId, customLimits, reason);
      await loadUserDetails();
      setEditingLimits(false);
      window.alert('Custom limits saved successfully');
    } catch (err) {
      window.alert(`Failed to save limits: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRemoveCustomLimits = async () => {
    if (!window.confirm('Remove custom limits? User will revert to subscription tier limits.')) return;

    try {
      setActionLoading(true);
      await APIService.removeUserCustomLimits(userId);
      await loadUserDetails();
      window.alert('Custom limits removed successfully');
    } catch (err) {
      window.alert(`Failed to remove custom limits: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleUpdateSubscription = async (newTier) => {
    if (!window.confirm(`Change subscription to ${newTier}?`)) return;

    try {
      setActionLoading(true);
      await APIService.updateUserSubscription(userId, newTier);
      await loadUserDetails(); // Reload to show updated data
      window.alert('Subscription updated successfully');
    } catch (err) {
      window.alert(`Failed to update subscription: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleActive = async () => {
    const newStatus = !userData.user.is_active;
    const action = newStatus ? 'activate' : 'deactivate';
    if (!window.confirm(`Are you sure you want to ${action} this user?`)) return;

    try {
      setActionLoading(true);
      await APIService.toggleUserActive(userId, newStatus);
      await loadUserDetails();
      window.alert(`User ${action}d successfully`);
    } catch (err) {
      window.alert(`Failed to ${action} user: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="admin-user-details">
        <div className="loading">Loading user details...</div>
      </div>
    );
  }

  if (error || !userData) {
    return (
      <div className="admin-user-details">
        <div className="error-message">Error: {error || 'User not found'}</div>
        <button
          onClick={() => {
            window.location.pathname = '/admin/users';
          }}
          className="btn-secondary"
        >
          ← Back to Users
        </button>
      </div>
    );
  }

  const { user, limits, statistics, recent_jobs } = userData;

  return (
    <div className="admin-user-details">
      <div className="user-header">
        <div>
          <h1>{user.email}</h1>
          <p className="user-meta">
            Created: {new Date(user.created_at).toLocaleString()} | 
            Last Login: {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
          </p>
        </div>
        <div className="header-actions">
          <button
            onClick={() => {
              window.location.pathname = '/admin/users';
            }}
            className="btn-secondary"
          >
            ← Back to Users
          </button>
          <button
            onClick={handleToggleActive}
            disabled={actionLoading}
            className={`btn-${user.is_active ? 'warning' : 'primary'}`}
          >
            {user.is_active ? 'Deactivate' : 'Activate'}
          </button>
        </div>
      </div>

      <div className="user-sections">
        {/* User Info */}
        <section className="info-section">
          <h2>User Information</h2>
          <div className="info-grid">
            <div className="info-item">
              <label>Name</label>
              <div>{user.first_name || ''} {user.last_name || ''}</div>
            </div>
            <div className="info-item">
              <label>Email</label>
              <div>{user.email}</div>
            </div>
            <div className="info-item info-item-full">
              <label>Subscription Tier</label>
              <div className="tier-selector">
                <span className={`tier-badge tier-${user.subscription_tier}`}>
                  {user.subscription_tier}
                </span>
                <div className="tier-buttons">
                  {['free', 'basic', 'pro', 'enterprise'].map(tier => (
                    <button
                      key={tier}
                      onClick={() => handleUpdateSubscription(tier)}
                      disabled={actionLoading || tier === user.subscription_tier}
                      className="btn-small"
                    >
                      {tier}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="info-item info-item-full">
              <label>Status</label>
              <div className="status-container">
                <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                  {user.is_active ? 'Active' : 'Inactive'}
                </span>
                {user.is_superuser && <span className="admin-badge">Admin</span>}
              </div>
            </div>
            <div className="info-item">
              <label>Credits</label>
              <div>Remaining: {user.credits_remaining} | Used this month: {user.credits_used_this_month}</div>
            </div>
          </div>
        </section>

        {/* Limits */}
        <section className="info-section">
          <div className="section-header">
            <h2>Current Limits</h2>
            <div className="section-actions">
              {!editingLimits ? (
                <>
                  <button
                    onClick={() => setEditingLimits(true)}
                    className="btn-primary"
                    disabled={actionLoading}
                  >
                    Edit Limits
                  </button>
                  {limits && limits.has_custom_limits && (
                    <button
                      onClick={handleRemoveCustomLimits}
                      className="btn-secondary"
                      disabled={actionLoading}
                    >
                      Remove Custom Limits
                    </button>
                  )}
                </>
              ) : (
                <>
                  <button
                    onClick={handleSaveLimits}
                    className="btn-primary"
                    disabled={actionLoading}
                  >
                    Save Limits
                  </button>
                  <button
                    onClick={() => {
                      setEditingLimits(false);
                      loadUserDetails(); // Reset to original values
                    }}
                    className="btn-secondary"
                    disabled={actionLoading}
                  >
                    Cancel
                  </button>
                </>
              )}
            </div>
          </div>
          {limits && limits.current_limits && (
            <div className="limits-grid">
              <div className="limit-item">
                <label>Max PDF Size</label>
                {editingLimits ? (
                  <div className="limit-input-group">
                    <input
                      type="number"
                      step="0.1"
                      value={limitValues.max_pdf_size !== undefined ? limitValues.max_pdf_size : bytesToMb(parseFileSize(limits.current_limits.max_pdf_size))}
                      onChange={(e) => setLimitValues({...limitValues, max_pdf_size: parseFloat(e.target.value) || 0})}
                      className="limit-input"
                    />
                    <span className="limit-unit">MB</span>
                  </div>
                ) : (
                  <div>{limits.current_limits.max_pdf_size}</div>
                )}
              </div>
              <div className="limit-item">
                <label>Max CSV Size</label>
                {editingLimits ? (
                  <div className="limit-input-group">
                    <input
                      type="number"
                      step="0.1"
                      value={limitValues.max_csv_size !== undefined ? limitValues.max_csv_size : bytesToMb(parseFileSize(limits.current_limits.max_csv_size))}
                      onChange={(e) => setLimitValues({...limitValues, max_csv_size: parseFloat(e.target.value) || 0})}
                      className="limit-input"
                    />
                    <span className="limit-unit">MB</span>
                  </div>
                ) : (
                  <div>{limits.current_limits.max_csv_size}</div>
                )}
              </div>
              <div className="limit-item">
                <label>Daily Jobs</label>
                {editingLimits ? (
                  <input
                    type="number"
                    value={limitValues.max_daily_jobs || limits.current_limits.max_daily_jobs}
                    onChange={(e) => setLimitValues({...limitValues, max_daily_jobs: e.target.value})}
                    className="limit-input"
                  />
                ) : (
                  <div>{limits.current_limits.max_daily_jobs}</div>
                )}
              </div>
              <div className="limit-item">
                <label>Monthly Jobs</label>
                {editingLimits ? (
                  <input
                    type="number"
                    value={limitValues.max_monthly_jobs || limits.current_limits.max_monthly_jobs}
                    onChange={(e) => setLimitValues({...limitValues, max_monthly_jobs: e.target.value})}
                    className="limit-input"
                  />
                ) : (
                  <div>{limits.current_limits.max_monthly_jobs}</div>
                )}
              </div>
              <div className="limit-item">
                <label>Files per Job</label>
                {editingLimits ? (
                  <input
                    type="number"
                    value={limitValues.max_files_per_job || limits.current_limits.max_files_per_job}
                    onChange={(e) => setLimitValues({...limitValues, max_files_per_job: e.target.value})}
                    className="limit-input"
                  />
                ) : (
                  <div>{limits.current_limits.max_files_per_job}</div>
                )}
              </div>
              <div className="limit-item">
                <label>Can Save Templates</label>
                {editingLimits ? (
                  <select
                    value={limitValues.can_save_templates !== undefined ? limitValues.can_save_templates : limits.current_limits.can_save_templates}
                    onChange={(e) => setLimitValues({...limitValues, can_save_templates: e.target.value === 'true'})}
                    className="limit-input"
                  >
                    <option value="true">Yes</option>
                    <option value="false">No</option>
                  </select>
                ) : (
                  <div>{limits.current_limits.can_save_templates ? 'Yes' : 'No'}</div>
                )}
              </div>
              <div className="limit-item">
                <label>Can Use API</label>
                {editingLimits ? (
                  <select
                    value={limitValues.can_use_api !== undefined ? limitValues.can_use_api : limits.current_limits.can_use_api}
                    onChange={(e) => setLimitValues({...limitValues, can_use_api: e.target.value === 'true'})}
                    className="limit-input"
                  >
                    <option value="true">Yes</option>
                    <option value="false">No</option>
                  </select>
                ) : (
                  <div>{limits.current_limits.can_use_api ? 'Yes' : 'No'}</div>
                )}
              </div>
            </div>
          )}
          {limits && limits.has_custom_limits && (
            <div className="custom-limits-notice">
              <strong>Custom Limits Enabled:</strong> {limits.custom_limits_reason}
            </div>
          )}
        </section>

        {/* Statistics */}
        <section className="info-section">
          <h2>Usage Statistics</h2>
          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-value">{statistics.total_jobs}</div>
              <div className="stat-label">Total Jobs</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{statistics.total_files}</div>
              <div className="stat-label">Total Files</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{statistics.total_templates}</div>
              <div className="stat-label">Saved Templates</div>
            </div>
          </div>
        </section>

        {/* Recent Jobs */}
        {recent_jobs && recent_jobs.length > 0 && (
          <section className="info-section">
            <h2>Recent Processing Jobs</h2>
            <div className="jobs-list">
              {recent_jobs.map(job => (
                <div key={job.id} className="job-item">
                  <div className="job-header">
                    <span className="job-status">{job.status}</span>
                    <span className="job-date">{new Date(job.created_at).toLocaleString()}</span>
                  </div>
                  <div className="job-details">
                    <div>Template: {job.template_filename}</div>
                    <div>CSV: {job.csv_filename}</div>
                    <div>PDFs: {job.successful_count} / {job.pdf_count}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

export default AdminUserDetails;


import React, { useState, useEffect } from 'react';
import APIService from '../../services/api';
import InlineMessage from '../UI/InlineMessage';
import './AdminUserDetails.css';

function AdminUserDetails() {
  // Extract userId from URL path (format: /admin/users/{userId})
  const pathParts = window.location.pathname.split('/');
  const userId = pathParts[pathParts.length - 1];
  const [userData, setUserData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState('success');
  const [actionLoading, setActionLoading] = useState(false);
  const [pendingTierChange, setPendingTierChange] = useState(null); // Store tier that's pending confirmation
  const [editingLimits, setEditingLimits] = useState(false);
  const [limitValues, setLimitValues] = useState({});
  const [reasonInput, setReasonInput] = useState(''); // For inline reason input
  const [showReasonInput, setShowReasonInput] = useState(false); // Show reason input when saving limits
  const [activityLogs, setActivityLogs] = useState([]);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [showActivityLogs, setShowActivityLogs] = useState(false);

  useEffect(() => {
    if (userId) {
      loadUserDetails();
    }
  }, [userId]);

  const loadActivityLogs = async () => {
    try {
      setLoadingLogs(true);
      const data = await APIService.getUserActivityLogs(userId, 100, 0);
      setActivityLogs(data.logs || []);
    } catch (err) {
      console.error('Failed to load activity logs:', err);
      showMessage(`Failed to load activity logs: ${err.message}`, 'error');
    } finally {
      setLoadingLogs(false);
    }
  };

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

  const handleSaveLimitsClick = () => {
    // Show reason input inline
    setShowReasonInput(true);
  };

  const handleSaveLimits = async () => {
    const reason = reasonInput.trim() || 'Admin override';
    try {
      setActionLoading(true);
      setShowReasonInput(false);
      
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
      
      await APIService.setUserCustomLimits(userId, customLimits, reason);
      await loadUserDetails();
      setEditingLimits(false);
      setReasonInput('');
      showMessage('Custom limits saved successfully');
    } catch (err) {
      showMessage(`Failed to save limits: ${err.message}`, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelEditLimits = () => {
    setEditingLimits(false);
    setShowReasonInput(false);
    setReasonInput('');
    loadUserDetails(); // Reset to original values
  };

  const handleRemoveCustomLimits = async () => {
    try {
      setActionLoading(true);
      await APIService.removeUserCustomLimits(userId);
      await loadUserDetails();
      showMessage('Custom limits removed successfully');
    } catch (err) {
      showMessage(`Failed to remove custom limits: ${err.message}`, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const showMessage = (msg, type = 'success') => {
    setMessage(msg);
    setMessageType(type);
    // Auto-clear after 5 seconds
    setTimeout(() => setMessage(null), 5000);
  };

  const handleUpdateSubscriptionClick = (newTier) => {
    // Set pending tier change to show inline confirmation
    setPendingTierChange(newTier);
  };

  const handleConfirmTierChange = async () => {
    const newTier = pendingTierChange;
    setPendingTierChange(null);
    try {
      setActionLoading(true);
      await APIService.updateUserSubscription(userId, newTier);
      await loadUserDetails(); // Reload to show updated data
      showMessage('Subscription updated successfully');
    } catch (err) {
      showMessage(`Failed to update subscription: ${err.message}`, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelTierChange = () => {
    setPendingTierChange(null);
  };

  const handleToggleActive = async () => {
    const newStatus = !userData.user.is_active;
    const action = newStatus ? 'activate' : 'deactivate';
    try {
      setActionLoading(true);
      await APIService.toggleUserActive(userId, newStatus);
      await loadUserDetails();
      showMessage(`User ${action}d successfully`);
    } catch (err) {
      showMessage(`Failed to ${action} user: ${err.message}`, 'error');
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
        <InlineMessage 
          message={error || 'User not found'}
          type="error"
        />
        <div style={{ textAlign: 'center', marginTop: '1rem' }}>
          <button
            onClick={() => {
              window.location.pathname = '/admin/users';
            }}
            className="btn-secondary"
          >
            ← Back to Users
          </button>
        </div>
      </div>
    );
  }

  const { user, limits, statistics, recent_jobs } = userData;

  return (
    <div className="admin-user-details">
      <InlineMessage 
        message={error ? `Error: ${error}` : message}
        type={error ? 'error' : messageType}
        onClose={error ? () => setError(null) : () => setMessage(null)}
      />


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
                  {['free', 'member', 'pro', 'enterprise'].map(tier => (
                    <React.Fragment key={tier}>
                      {pendingTierChange === tier ? (
                        <div className="inline-confirmation">
                          <span className="confirmation-message">Change to {tier}? (This will remove custom limits)</span>
                          <button
                            onClick={handleConfirmTierChange}
                            disabled={actionLoading}
                            className="btn-primary btn-small"
                          >
                            Confirm
                          </button>
                          <button
                            onClick={handleCancelTierChange}
                            disabled={actionLoading}
                            className="btn-secondary btn-small"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleUpdateSubscriptionClick(tier)}
                          disabled={actionLoading || tier === user.subscription_tier || pendingTierChange !== null}
                          className="btn-small"
                        >
                          {tier}
                        </button>
                      )}
                    </React.Fragment>
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
                  {showReasonInput ? (
                    <div className="inline-reason-input">
                      <input
                        type="text"
                        placeholder="Reason for custom limits (optional)"
                        value={reasonInput}
                        onChange={(e) => setReasonInput(e.target.value)}
                        className="reason-input"
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') {
                            handleSaveLimits();
                          }
                        }}
                      />
                      <button
                        onClick={handleSaveLimits}
                        className="btn-primary"
                        disabled={actionLoading}
                      >
                        Confirm Changes
                      </button>
                      <button
                        onClick={() => {
                          setShowReasonInput(false);
                          setReasonInput('');
                        }}
                        className="btn-secondary"
                        disabled={actionLoading}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <>
                      <button
                        onClick={handleSaveLimitsClick}
                        className="btn-primary"
                        disabled={actionLoading}
                      >
                        Save Limits
                      </button>
                      <button
                        onClick={handleCancelEditLimits}
                        className="btn-secondary"
                        disabled={actionLoading}
                      >
                        Discard Changes
                      </button>
                    </>
                  )}
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

        {/* Activity Log History */}
        <section className="info-section">
          <div className="section-header">
            <h2>Activity History</h2>
            <button
              onClick={() => {
                if (!showActivityLogs) {
                  loadActivityLogs();
                }
                setShowActivityLogs(!showActivityLogs);
              }}
              className="btn-secondary"
            >
              {showActivityLogs ? 'Hide' : 'Show'} Activity Logs
            </button>
          </div>
          {showActivityLogs && (
            <div className="activity-logs">
              {loadingLogs ? (
                <div className="loading">Loading activity logs...</div>
              ) : activityLogs.length === 0 ? (
                <div className="no-logs">No activity logs found</div>
              ) : (
                <div className="logs-list">
                  {activityLogs.map(log => (
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
                      {log.reason && (
                        <div className="log-reason">
                          <strong>Reason:</strong> {log.reason}
                        </div>
                      )}
                      {log.changes && (
                        <div className="log-changes">
                          <strong>Changes:</strong>
                          <pre>{JSON.stringify(log.changes, null, 2)}</pre>
                        </div>
                      )}
                      <div className="log-metadata">
                        {log.ip_address && <span>IP: {log.ip_address}</span>}
                        {log.country && <span>Country: {log.country}</span>}
                        {log.actor_type && <span>Actor: {log.actor_type}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default AdminUserDetails;


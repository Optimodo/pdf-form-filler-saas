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
  const [editingCredits, setEditingCredits] = useState(false);
  const [creditValues, setCreditValues] = useState({});
  const [activityLogs, setActivityLogs] = useState([]);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [showActivityLogs, setShowActivityLogs] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [jobsPage, setJobsPage] = useState(1);
  const [jobsPagination, setJobsPagination] = useState(null);
  const [availableTiers, setAvailableTiers] = useState([]);

  useEffect(() => {
    if (userId) {
      loadUserDetails();
      loadJobs(1);
    }
    loadTiers();
  }, [userId]);

  const loadTiers = async () => {
    try {
      const data = await APIService.listSubscriptionTiers();
      // Filter to only active tiers and sort by display_order
      const activeTiers = (data.tiers || [])
        .filter(tier => tier.is_active)
        .sort((a, b) => (a.display_order || 999) - (b.display_order || 999));
      setAvailableTiers(activeTiers);
    } catch (err) {
      console.error('Failed to load tiers:', err);
      // If loading fails, we'll just not show tier buttons
      setAvailableTiers([]);
    }
  };

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

  const loadJobs = async (page = 1) => {
    try {
      setLoadingJobs(true);
      const data = await APIService.getUserJobs(userId, page, 10);
      setJobs(data.jobs || []);
      setJobsPagination(data.pagination);
      setJobsPage(page);
    } catch (err) {
      console.error('Failed to load jobs:', err);
      showMessage(`Failed to load jobs: ${err.message}`, 'error');
    } finally {
      setLoadingJobs(false);
    }
  };

  const handleFileDownload = async (url, filename) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to download file');
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error('Download error:', err);
      showMessage(`Failed to download file: ${err.message}`, 'error');
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
          max_pdfs_per_run: limits.max_pdfs_per_run,
          can_save_templates: limits.can_save_templates,
          can_use_api: limits.can_use_api,
        });
      }
      
      // Initialize credit values for editing
      if (data.user) {
        setCreditValues({
          credits_remaining: data.user.credits_remaining,
          credits_rollover: data.user.credits_rollover,
          credits_used_this_month: data.user.credits_used_this_month,
          credits_used_total: data.user.credits_used_total,
          total_pdf_runs: data.user.total_pdf_runs,
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
        max_pdfs_per_run: parseInt(limitValues.max_pdfs_per_run),
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

  const handleSaveCredits = async () => {
    try {
      setActionLoading(true);
      await APIService.updateUserCredits(userId, creditValues);
      await loadUserDetails();
      setEditingCredits(false);
      showMessage('Credits updated successfully');
    } catch (err) {
      showMessage(`Failed to update credits: ${err.message}`, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelEditCredits = () => {
    setEditingCredits(false);
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

  const { user, limits, statistics } = userData;

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
                  {availableTiers.find(t => t.tier_key === user.subscription_tier)?.display_name || user.subscription_tier}
                </span>
                <div className="tier-buttons">
                  {availableTiers.map(tier => (
                    <React.Fragment key={tier.tier_key}>
                      {pendingTierChange === tier.tier_key ? (
                        <div className="inline-confirmation">
                          <span className="confirmation-message">Change to {tier.display_name}? (This will remove custom limits)</span>
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
                          onClick={() => handleUpdateSubscriptionClick(tier.tier_key)}
                          disabled={actionLoading || tier.tier_key === user.subscription_tier || pendingTierChange !== null}
                          className="btn-small"
                          title={tier.description || tier.display_name}
                        >
                          {tier.display_name}
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
          </div>
        </section>

        {/* Credits Management */}
        <section className="info-section">
          <div className="section-header">
            <h2>Credits Management</h2>
            <div className="section-actions">
              {!editingCredits ? (
                <button
                  onClick={() => setEditingCredits(true)}
                  className="btn-primary"
                  disabled={actionLoading}
                >
                  Edit Credits
                </button>
              ) : (
                <>
                  <button
                    onClick={handleSaveCredits}
                    className="btn-primary"
                    disabled={actionLoading}
                  >
                    Save Credits
                  </button>
                  <button
                    onClick={handleCancelEditCredits}
                    className="btn-secondary"
                    disabled={actionLoading}
                  >
                    Cancel
                  </button>
                </>
              )}
            </div>
          </div>
          <div className="credits-grid">
            <div className="credit-item">
              <label>Credits Remaining (Top-up)</label>
              {editingCredits ? (
                <input
                  type="number"
                  value={creditValues.credits_remaining !== undefined ? creditValues.credits_remaining : user.credits_remaining}
                  onChange={(e) => setCreditValues({...creditValues, credits_remaining: parseInt(e.target.value) || 0})}
                  className="credit-input"
                  min="0"
                />
              ) : (
                <div>{user.credits_remaining}</div>
              )}
            </div>
            <div className="credit-item">
              <label>Credits Rollover</label>
              {editingCredits ? (
                <input
                  type="number"
                  value={creditValues.credits_rollover !== undefined ? creditValues.credits_rollover : user.credits_rollover}
                  onChange={(e) => setCreditValues({...creditValues, credits_rollover: parseInt(e.target.value) || 0})}
                  className="credit-input"
                  min="0"
                />
              ) : (
                <div>{user.credits_rollover}</div>
              )}
            </div>
            <div className="credit-item">
              <label>Credits Used This Month</label>
              {editingCredits ? (
                <input
                  type="number"
                  value={creditValues.credits_used_this_month !== undefined ? creditValues.credits_used_this_month : user.credits_used_this_month}
                  onChange={(e) => setCreditValues({...creditValues, credits_used_this_month: parseInt(e.target.value) || 0})}
                  className="credit-input"
                  min="0"
                />
              ) : (
                <div>{user.credits_used_this_month}</div>
              )}
            </div>
            <div className="credit-item">
              <label>Total Credits Used (Lifetime)</label>
              {editingCredits ? (
                <input
                  type="number"
                  value={creditValues.credits_used_total !== undefined ? creditValues.credits_used_total : user.credits_used_total}
                  onChange={(e) => setCreditValues({...creditValues, credits_used_total: parseInt(e.target.value) || 0})}
                  className="credit-input"
                  min="0"
                />
              ) : (
                <div>{user.credits_used_total}</div>
              )}
            </div>
            <div className="credit-item">
              <label>Total PDF Runs</label>
              {editingCredits ? (
                <input
                  type="number"
                  value={creditValues.total_pdf_runs !== undefined ? creditValues.total_pdf_runs : user.total_pdf_runs}
                  onChange={(e) => setCreditValues({...creditValues, total_pdf_runs: parseInt(e.target.value) || 0})}
                  className="credit-input"
                  min="0"
                />
              ) : (
                <div>{user.total_pdf_runs}</div>
              )}
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
                <label>Max PDFs per Run</label>
                {editingLimits ? (
                  <input
                    type="number"
                    value={limitValues.max_pdfs_per_run !== undefined ? limitValues.max_pdfs_per_run : limits.current_limits.max_pdfs_per_run}
                    onChange={(e) => setLimitValues({...limitValues, max_pdfs_per_run: parseInt(e.target.value) || 0})}
                    className="limit-input"
                  />
                ) : (
                  <div>{limits.current_limits.max_pdfs_per_run}</div>
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
              <div className="stat-value">{statistics.total_pdf_runs}</div>
              <div className="stat-label">Total PDF Runs</div>
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

        {/* Processing Jobs */}
        <section className="info-section">
          <h2>Processing Jobs</h2>
          {loadingJobs ? (
            <div className="loading">Loading jobs...</div>
          ) : jobs.length > 0 ? (
            <>
              <div className="jobs-list-compact">
                {/* Header row */}
                <div className="job-item-compact job-header-row">
                  <div>Status</div>
                  <div>Template</div>
                  <div>CSV</div>
                  <div>PDFs</div>
                  <div>Date</div>
                  <div>Actions</div>
                </div>
                {jobs.map(job => (
                  <div key={job.id} className="job-item-compact">
                    <span className={`job-status job-status-${job.status}`}>{job.status}</span>
                    <div className="job-template-col">
                      {job.template_file ? (
                        <button
                          onClick={() => handleFileDownload(
                            APIService.getFileDownloadUrl(job.template_file.id),
                            job.template_file.original_filename
                          )}
                          className="job-file-link btn-link"
                          title={job.template_file.original_filename}
                        >
                          {job.template_filename}
                        </button>
                      ) : (
                        <span title={job.template_filename}>{job.template_filename}</span>
                      )}
                    </div>
                    <div className="job-csv-col">
                      {job.csv_file ? (
                        <button
                          onClick={() => handleFileDownload(
                            APIService.getFileDownloadUrl(job.csv_file.id),
                            job.csv_file.original_filename
                          )}
                          className="job-file-link btn-link"
                          title={job.csv_file.original_filename}
                        >
                          {job.csv_filename}
                        </button>
                      ) : (
                        <span title={job.csv_filename}>{job.csv_filename}</span>
                      )}
                    </div>
                    <div className="job-pdfs-col">
                      {job.successful_count} / {job.pdf_count}
                    </div>
                    <span className="job-date-compact">{new Date(job.created_at).toLocaleString()}</span>
                    <div className="job-actions-col">
                      {job.zip_filename && job.zip_file_path && (
                        <button
                          onClick={() => handleFileDownload(
                            APIService.getJobZipDownloadUrl(job.id),
                            job.zip_filename
                          )}
                          className="btn-link"
                          title="Download ZIP output"
                        >
                          ZIP
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              {jobsPagination && jobsPagination.total_pages > 1 && (
                <div className="jobs-pagination">
                  <button
                    onClick={() => loadJobs(jobsPage - 1)}
                    disabled={jobsPage === 1 || loadingJobs}
                    className="btn-secondary btn-small"
                  >
                    Previous
                  </button>
                  <span className="pagination-info">
                    Page {jobsPage} of {jobsPagination.total_pages} ({jobsPagination.total_count} total)
                  </span>
                  <button
                    onClick={() => loadJobs(jobsPage + 1)}
                    disabled={jobsPage >= jobsPagination.total_pages || loadingJobs}
                    className="btn-secondary btn-small"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="no-jobs">No processing jobs found</div>
          )}
        </section>

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
                  {/* Header row */}
                  <div className="log-item log-header-row">
                    <div>Category</div>
                    <div>Type</div>
                    <div>Action</div>
                    <div>Description</div>
                    <div>Date</div>
                  </div>
                  {activityLogs.map(log => (
                    <div key={log.id} className="log-item">
                      <span className={`log-category log-category-${log.category}`}>
                        {log.category}
                      </span>
                      <span className="log-type">{log.activity_type.replace(/_/g, ' ')}</span>
                      <div className="log-action">{log.action}</div>
                      <div className="log-description">
                        {log.description || '-'}
                      </div>
                      <span className="log-date">{new Date(log.created_at).toLocaleString()}</span>
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
                      {(log.ip_address || log.country || log.actor_type) && (
                        <div className="log-metadata">
                          {log.ip_address && <span>IP: {log.ip_address}</span>}
                          {log.country && <span>Country: {log.country}</span>}
                          {log.actor_type && <span>Actor: {log.actor_type}</span>}
                        </div>
                      )}
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






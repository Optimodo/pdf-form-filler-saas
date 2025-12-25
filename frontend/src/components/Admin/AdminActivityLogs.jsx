import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import APIService from '../../services/api';
import './AdminActivityLogs.css';

function AdminActivityLogs() {
  const { user, isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState('admin'); // 'admin' or 'jobs'
  
  // Admin logs state
  const [adminLogs, setAdminLogs] = useState([]);
  const [loadingAdminLogs, setLoadingAdminLogs] = useState(true);
  const [adminLogsError, setAdminLogsError] = useState(null);
  const [adminLogsTotal, setAdminLogsTotal] = useState(0);
  const [adminLogsSkip, setAdminLogsSkip] = useState(0);
  const adminLogsLimit = 50;
  
  // PDF jobs state
  const [jobs, setJobs] = useState([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [jobsError, setJobsError] = useState(null);
  const [jobsPage, setJobsPage] = useState(1);
  const [jobsPagination, setJobsPagination] = useState(null);
  const jobsLimit = 10;
  const [jobFilters, setJobFilters] = useState({
    userEmail: '',
    userTier: ''
  });
  
  // Get subscription tiers for filter
  const [tiers, setTiers] = useState([]);
  
  useEffect(() => {
    if (!isAuthenticated || !user) {
      setAdminLogsError('You must be logged in to access the admin panel.');
      setLoadingAdminLogs(false);
      return;
    }

    if (!user.is_superuser) {
      setAdminLogsError('Access denied. Admin privileges required.');
      setLoadingAdminLogs(false);
      return;
    }

    loadTiers();
    if (activeTab === 'admin') {
      loadAdminLogs();
    } else {
      loadJobs();
    }
  }, [isAuthenticated, user, activeTab, adminLogsSkip, jobsPage, jobFilters]);

  const loadTiers = async () => {
    try {
      const data = await APIService.listSubscriptionTiers();
      setTiers(data.tiers || []);
    } catch (err) {
      console.error('Error loading tiers:', err);
    }
  };

  const loadAdminLogs = async () => {
    try {
      setLoadingAdminLogs(true);
      // Only fetch admin-related activity logs
      const data = await APIService.getSystemActivityLogs('admin', null, adminLogsLimit, adminLogsSkip);
      setAdminLogs(data.logs || []);
      setAdminLogsTotal(data.total || 0);
      setAdminLogsError(null);
    } catch (err) {
      setAdminLogsError(err.message || 'Failed to load admin activity logs');
      console.error('Admin logs error:', err);
    } finally {
      setLoadingAdminLogs(false);
    }
  };

  const loadJobs = async () => {
    try {
      setLoadingJobs(true);
      const data = await APIService.getAllJobs(
        jobsPage,
        jobsLimit,
        jobFilters.userEmail || null,
        jobFilters.userTier || null
      );
      setJobs(data.jobs || []);
      setJobsPagination(data.pagination || null);
      setJobsError(null);
    } catch (err) {
      setJobsError(err.message || 'Failed to load PDF jobs');
      console.error('Jobs error:', err);
    } finally {
      setLoadingJobs(false);
    }
  };

  const handleJobFilterChange = (field, value) => {
    setJobFilters(prev => ({ ...prev, [field]: value }));
    setJobsPage(1); // Reset to first page when filter changes
  };

  const handleFileDownload = async (url, filename) => {
    try {
      const response = await fetch(url, {
        headers: APIService.getAuthHeaders(),
      });
      if (!response.ok) throw new Error('Download failed');
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download error:', err);
      alert('Failed to download file');
    }
  };

  const handlePreviousAdminPage = () => {
    if (adminLogsSkip > 0) {
      setAdminLogsSkip(Math.max(0, adminLogsSkip - adminLogsLimit));
    }
  };

  const handleNextAdminPage = () => {
    if (adminLogsSkip + adminLogsLimit < adminLogsTotal) {
      setAdminLogsSkip(adminLogsSkip + adminLogsLimit);
    }
  };

  const handlePreviousJobsPage = () => {
    if (jobsPage > 1) {
      setJobsPage(jobsPage - 1);
    }
  };

  const handleNextJobsPage = () => {
    if (jobsPagination && jobsPage < jobsPagination.total_pages) {
      setJobsPage(jobsPage + 1);
    }
  };

  const formatActivityType = (type) => {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  if (adminLogsError && !user?.is_superuser) {
    return (
      <div className="admin-activity-logs">
        <h1>System Activity Logs</h1>
        <div className="error-message">Error: {adminLogsError}</div>
        {adminLogsError.includes('Access denied') || adminLogsError.includes('must be logged in') ? (
          <button
            onClick={() => {
              window.location.pathname = '/';
            }}
            className="btn-primary"
          >
            Return to Home
          </button>
        ) : (
          <button onClick={loadAdminLogs} className="btn-primary">Retry</button>
        )}
      </div>
    );
  }

  return (
    <div className="admin-activity-logs">
      <div className="header-section">
        <h1>Activity Logs</h1>
        <button
          onClick={() => {
            window.location.pathname = '/admin';
          }}
          className="btn-secondary"
        >
          ← Back to Dashboard
        </button>
      </div>

      {/* Tabs */}
      <div className="tabs">
        <button
          className={`tab-button ${activeTab === 'admin' ? 'active' : ''}`}
          onClick={() => setActiveTab('admin')}
        >
          Admin Activity Log
        </button>
        <button
          className={`tab-button ${activeTab === 'jobs' ? 'active' : ''}`}
          onClick={() => setActiveTab('jobs')}
        >
          PDF Job Activity Log
        </button>
      </div>

      {/* Admin Activity Log Tab */}
      {activeTab === 'admin' && (
        <div className="tab-content">
          {loadingAdminLogs && adminLogs.length === 0 ? (
            <div className="loading">Loading admin activity logs...</div>
          ) : adminLogsError && adminLogs.length === 0 ? (
            <div className="error-message">Error: {adminLogsError}</div>
          ) : adminLogs.length === 0 ? (
            <div className="no-logs">No admin activity logs found</div>
          ) : (
            <>
              <div className="logs-summary">
                Showing {adminLogs.length} of {adminLogsTotal} admin activity logs
              </div>
              
              <div className="logs-list-compact">
                {/* Header row */}
                <div className="log-item log-header-row">
                  <div>Type</div>
                  <div>Action</div>
                  <div>Description</div>
                  <div>Date</div>
                </div>
                
                {adminLogs.map(log => (
                  <div key={log.id} className="log-item">
                    <span className="log-type">{formatActivityType(log.activity_type)}</span>
                    <div className="log-action">{log.action}</div>
                    <div className="log-description">{log.description || '-'}</div>
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
                  </div>
                ))}
              </div>

              <div className="pagination">
                <button
                  onClick={handlePreviousAdminPage}
                  disabled={adminLogsSkip === 0}
                  className="btn-secondary"
                >
                  Previous
                </button>
                <span className="pagination-info">
                  Page {Math.floor(adminLogsSkip / adminLogsLimit) + 1} of {Math.ceil(adminLogsTotal / adminLogsLimit)}
                </span>
                <button
                  onClick={handleNextAdminPage}
                  disabled={adminLogsSkip + adminLogsLimit >= adminLogsTotal}
                  className="btn-secondary"
                >
                  Next
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* PDF Job Activity Log Tab */}
      {activeTab === 'jobs' && (
        <div className="tab-content">
          {/* Filters */}
          <div className="jobs-filters">
            <div className="filter-group">
              <label htmlFor="user-email-filter">User Email:</label>
              <input
                id="user-email-filter"
                type="text"
                value={jobFilters.userEmail}
                onChange={(e) => handleJobFilterChange('userEmail', e.target.value)}
                placeholder="Filter by email..."
                className="filter-input"
              />
            </div>
            
            <div className="filter-group">
              <label htmlFor="user-tier-filter">Subscription Tier:</label>
              <select
                id="user-tier-filter"
                value={jobFilters.userTier}
                onChange={(e) => handleJobFilterChange('userTier', e.target.value)}
                className="filter-select"
              >
                <option value="">All Tiers</option>
                <option value="anonymous">Anonymous</option>
                {tiers.map(tier => (
                  <option key={tier.id} value={tier.tier_key}>
                    {tier.display_name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {loadingJobs && jobs.length === 0 ? (
            <div className="loading">Loading PDF jobs...</div>
          ) : jobsError && jobs.length === 0 ? (
            <div className="error-message">Error: {jobsError}</div>
          ) : jobs.length === 0 ? (
            <div className="no-logs">No PDF jobs found</div>
          ) : (
            <>
              {jobsPagination && (
                <div className="logs-summary">
                  Showing {jobs.length} of {jobsPagination.total_count} jobs
                </div>
              )}
              
              <div className="jobs-list-compact">
                {/* Header row */}
                <div className="job-item-compact job-header-row">
                  <div>User</div>
                  <div>Status</div>
                  <div>Template</div>
                  <div>CSV</div>
                  <div>PDFs</div>
                  <div>Date</div>
                  <div>Actions</div>
                </div>
                
                {jobs.map(job => (
                  <div key={job.id} className="job-item-compact">
                    <div className="job-user-col">
                      {job.user ? (
                        <span title={job.user.email}>
                          {job.user.email}
                          {job.user.subscription_tier && (
                            <span className="tier-badge-small">{job.user.subscription_tier}</span>
                          )}
                        </span>
                      ) : (
                        <span className="anonymous-user">Anonymous</span>
                      )}
                    </div>
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
                      {job.zip_filename && (
                        <button
                          onClick={() => handleFileDownload(
                            APIService.getJobZipDownloadUrl(job.id),
                            job.zip_filename
                          )}
                          className="btn-link"
                          title="Download ZIP"
                        >
                          ZIP
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {jobsPagination && (
                <div className="pagination">
                  <button
                    onClick={handlePreviousJobsPage}
                    disabled={jobsPage === 1}
                    className="btn-secondary"
                  >
                    Previous
                  </button>
                  <span className="pagination-info">
                    Page {jobsPage} of {jobsPagination.total_pages}
                  </span>
                  <button
                    onClick={handleNextJobsPage}
                    disabled={jobsPage >= jobsPagination.total_pages}
                    className="btn-secondary"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default AdminActivityLogs;




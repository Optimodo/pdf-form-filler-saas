import React, { useState, useEffect } from 'react';
import APIService from '../../services/api';
import './ProcessingHistory.css';

const ProcessingHistory = () => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await APIService.getProcessingHistory(50);
      const jobsData = data.processing_history || [];
      // Debug: log first job to see structure
      if (jobsData.length > 0) {
        console.log('ProcessingHistory - First job data:', jobsData[0]);
      }
      setJobs(jobsData);
    } catch (err) {
      setError(err.message || 'Failed to load processing history');
      console.error('Processing history error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileDownload = async (fileId, originalFilename) => {
    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const url = `${apiUrl}/api/pdf/download-file/${fileId}`;
      
      const response = await fetch(url, {
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
      });

      if (!response.ok) {
        throw new Error('Failed to download file');
      }

      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = originalFilename;
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(blobUrl);
      document.body.removeChild(link);
    } catch (err) {
      console.error('File download error:', err);
      alert('Failed to download file. Please try again.');
    }
  };

  const handleZipDownload = async (job) => {
    if (job.zip_filename && job.session_id) {
      try {
        // Use the existing download-zip endpoint
        const token = localStorage.getItem('access_token');
        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
        const url = `${apiUrl}/api/pdf/download-zip/${encodeURIComponent(job.zip_filename)}?session_id=${encodeURIComponent(job.session_id)}`;
        
        const response = await fetch(url, {
          headers: {
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          },
        });

        if (!response.ok) {
          throw new Error('Failed to download ZIP file');
        }

        const blob = await response.blob();
        const blobUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = job.zip_filename;
        document.body.appendChild(link);
        link.click();
        window.URL.revokeObjectURL(blobUrl);
        document.body.removeChild(link);
      } catch (err) {
        console.error('ZIP download error:', err);
        alert('Failed to download ZIP file. Please try again.');
      }
    }
  };

  const formatCreditsBreakdown = (job) => {
    const parts = [];
    if (job.subscription_credits_used > 0) {
      parts.push(`${job.subscription_credits_used} monthly`);
    }
    if (job.rollover_credits_used > 0) {
      parts.push(`${job.rollover_credits_used} rollover`);
    }
    if (job.topup_credits_used > 0) {
      parts.push(`${job.topup_credits_used} top-up`);
    }
    return parts.length > 0 ? parts.join(', ') : '0';
  };

  if (loading) {
    return (
      <div className="processing-history">
        <div className="loading">Loading processing history...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="processing-history">
        <div className="error-message">
          <p>Error: {error}</p>
          <button onClick={loadHistory} className="btn-secondary">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="processing-history">
        <div className="history-placeholder">
          <div className="placeholder-icon">📋</div>
          <h3>No Processing History</h3>
          <p>Your PDF processing jobs will appear here once you start using the service.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="processing-history">
      <div className="history-header">
        <h2>Processing History</h2>
        <p className="history-subtitle">View and download your past PDF processing jobs</p>
      </div>

      <div className="jobs-list-compact">
        {/* Header row */}
        <div className="job-item-compact job-header-row">
          <div>Status</div>
          <div>Template</div>
          <div>CSV</div>
          <div>PDFs</div>
          <div>Credits Used</div>
          <div>Date</div>
          <div>Actions</div>
        </div>

        {jobs.map(job => (
          <div key={job.id} className="job-item-compact">
            <span className={`job-status job-status-${job.status?.toLowerCase() || 'unknown'}`}>
              {job.status || 'unknown'}
            </span>
            
            <div className="job-template-col">
              {job.template_file ? (
                <button
                  onClick={() => handleFileDownload(job.template_file.id, job.template_file.original_filename)}
                  className="job-file-link btn-link"
                  title={job.template_file.original_filename}
                >
                  {job.template_file.original_filename || job.template_filename || 'Template File'}
                </button>
              ) : job.template_filename ? (
                <span title={job.template_filename}>{job.template_filename}</span>
              ) : (
                <span className="text-muted">N/A</span>
              )}
            </div>
            
            <div className="job-csv-col">
              {job.csv_file ? (
                <button
                  onClick={() => handleFileDownload(job.csv_file.id, job.csv_file.original_filename)}
                  className="job-file-link btn-link"
                  title={job.csv_file.original_filename}
                >
                  {job.csv_file.original_filename || job.csv_filename || 'CSV File'}
                </button>
              ) : job.csv_filename ? (
                <span title={job.csv_filename}>{job.csv_filename}</span>
              ) : (
                <span className="text-muted">N/A</span>
              )}
            </div>
            
            <div className="job-pdfs-col">
              {job.successful_count || 0} / {job.pdf_count || 0}
              {job.failed_count > 0 && (
                <span className="job-failed-count"> ({job.failed_count} failed)</span>
              )}
            </div>
            
            <div className="job-credits-col">
              <div className="job-credits-info">
                <div className="job-credits-total">
                  <strong>{job.total_credits_consumed || 0}</strong> total
                </div>
                <div className="job-credits-breakdown">
                  {formatCreditsBreakdown(job)}
                </div>
              </div>
            </div>
            
            <span className="job-date-compact">
              {job.created_at ? new Date(job.created_at).toLocaleString() : '—'}
            </span>
            
            <div className="job-actions-col">
              {job.zip_filename && job.session_id ? (
                <button
                  onClick={() => handleZipDownload(job)}
                  className="btn-link"
                  title="Download ZIP file"
                >
                  ZIP
                </button>
              ) : (
                <span className="text-muted">—</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ProcessingHistory;





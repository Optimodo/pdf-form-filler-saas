import React, { useState, useEffect } from 'react';
import APIService from '../../services/api';

const FileLimits = () => {
  const [limits, setLimits] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchLimits = async () => {
      try {
        const userLimits = await APIService.getUserLimits();
        setLimits(userLimits);
      } catch (err) {
        console.error('Failed to fetch user limits:', err);
        setError('Failed to load file size limits');
      } finally {
        setLoading(false);
      }
    };

    fetchLimits();
  }, []);

  if (loading) {
    return (
      <div className="file-limits loading">
        <span className="limits-icon">⚡</span>
        <span>Loading limits...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="file-limits error">
        <span className="limits-icon">⚠️</span>
        <span>{error}</span>
      </div>
    );
  }

  if (!limits) return null;

  const getTierColor = (tier) => {
    switch (tier) {
      case 'free': return '#6b7280';
      case 'basic': return '#3b82f6';
      case 'pro': return '#8b5cf6';
      case 'enterprise': return '#f59e0b';
      case 'anonymous': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getTierDisplayName = (tier) => {
    if (tier === 'anonymous') return 'Trial User';
    return tier.charAt(0).toUpperCase() + tier.slice(1);
  };

  return (
    <div className="file-limits">
      <div className="limits-header">
        <span className="limits-icon">📁</span>
        <div className="limits-title">
          <span className="limits-text">File Size Limits</span>
          <span 
            className="limits-tier"
            style={{ color: getTierColor(limits.subscription_tier) }}
          >
            {getTierDisplayName(limits.subscription_tier)}
          </span>
        </div>
      </div>
      
      <div className="limits-details">
        <div className="limit-item">
          <span className="limit-label">PDF Template:</span>
          <span className="limit-value">{limits.max_pdf_size_display}</span>
        </div>
        <div className="limit-item">
          <span className="limit-label">CSV Data:</span>
          <span className="limit-value">{limits.max_csv_size_display}</span>
        </div>
        {limits.subscription_tier === 'anonymous' && (
          <div className="upgrade-hint">
            <span className="upgrade-icon">💡</span>
            <span>Sign up for larger file limits!</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default FileLimits;

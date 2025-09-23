import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import APIService from '../../services/api';

const FileLimitNote = ({ fileType }) => {
  const { isAuthenticated } = useAuth();
  const [limits, setLimits] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLimits = async () => {
      try {
        const userLimits = await APIService.getUserLimits();
        setLimits(userLimits);
      } catch (err) {
        console.error('Failed to fetch user limits:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchLimits();
  }, [isAuthenticated]);

  if (loading || !limits) {
    return (
      <div className="file-limit-note loading">
        Loading limits...
      </div>
    );
  }

  const getFileLimit = () => {
    if (fileType === 'pdf') {
      return limits.max_pdf_size_display;
    } else if (fileType === 'csv') {
      return limits.max_csv_size_display;
    }
    return '';
  };

  const isAnonymous = limits.subscription_tier === 'anonymous';
  const isFree = limits.subscription_tier === 'free';

  return (
    <div className="file-limit-note">
      <span className="limit-text">
        Max size: <strong>{getFileLimit()}</strong>
      </span>
      {(isAnonymous || isFree) && (
        <span className="upgrade-link">
          • <button type="button" className="link-style">Sign up to increase limits</button>
        </span>
      )}
    </div>
  );
};

export default FileLimitNote;

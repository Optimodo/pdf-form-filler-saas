import React from 'react';

const ProgressBar = ({ progress = 0, status = '', isVisible = false }) => {
  if (!isVisible) return null;

  return (
    <div className="progress-container">
      <div className="progress-bar">
        <div 
          className="progress-fill" 
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>
      <div className="progress-text">
        {status && (
          <span className="progress-status">{status}</span>
        )}
        <span className="progress-percentage">{Math.round(progress)}%</span>
      </div>
    </div>
  );
};

export default ProgressBar;

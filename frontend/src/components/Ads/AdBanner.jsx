import React from 'react';

const AdBanner = ({ size = 'medium', position = 'top' }) => {
  // In real app, this would check user tier and show/hide ads
  const isFreeTier = true; // Demo - would come from user context
  
  if (!isFreeTier) {
    return null; // Hide ads for paid users
  }

  const sizeClasses = {
    small: 'ad-banner-small',
    medium: 'ad-banner-medium',
    large: 'ad-banner-large'
  };

  return (
    <div className={`ad-banner ${sizeClasses[size]} ad-banner-${position}`}>
      <div className="ad-placeholder">
        <span className="ad-text">Ad Space</span>
        <span className="ad-size">{size === 'medium' ? '300x100' : size}</span>
      </div>
    </div>
  );
};

export default AdBanner;

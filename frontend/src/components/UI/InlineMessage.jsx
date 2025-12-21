import React from 'react';
import './InlineMessage.css';

function InlineMessage({ message, type = 'success', onClose }) {
  if (!message) return null;

  return (
    <div className={`inline-message inline-message-${type}`}>
      <span className="inline-message-text">{message}</span>
      {onClose && (
        <button className="inline-message-close" onClick={onClose} aria-label="Close">
          ×
        </button>
      )}
    </div>
  );
}

export default InlineMessage;


import React, { useState, useEffect } from 'react';
import './InputDialog.css';

function InputDialog({ 
  isOpen, 
  title, 
  message, 
  placeholder = '',
  defaultValue = '',
  confirmText = 'Confirm', 
  cancelText = 'Cancel',
  onConfirm, 
  onCancel,
  inputType = 'text',
  required = false // Whether input is required (false allows empty)
}) {
  const [inputValue, setInputValue] = useState(defaultValue);

  useEffect(() => {
    if (isOpen) {
      setInputValue(defaultValue);
    }
  }, [isOpen, defaultValue]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm(inputValue);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleConfirm();
    }
  };

  return (
    <div className="input-dialog-overlay" onClick={onCancel}>
      <div className="input-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="input-dialog-header">
          <h3>{title || 'Input Required'}</h3>
        </div>
        <div className="input-dialog-body">
          {message && <p>{message}</p>}
          <input
            type={inputType}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={placeholder}
            className="input-dialog-input"
            autoFocus
          />
        </div>
        <div className="input-dialog-actions">
          <button 
            onClick={onCancel} 
            className="btn-secondary input-dialog-cancel"
          >
            {cancelText}
          </button>
          <button 
            onClick={handleConfirm} 
            className="btn-primary"
            disabled={required && !inputValue.trim()}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

export default InputDialog;


import React, { useState, useEffect } from 'react';
import './Toast.css';

const ToastContext = React.createContext();

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = (message, type = 'success') => {
    const id = Date.now() + Math.random();
    const toast = { id, message, type };
    setToasts(prev => [...prev, toast]);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      removeToast(id);
    }, 5000);
    
    return id;
  };

  const removeToast = (id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  const showSuccess = (message) => addToast(message, 'success');
  const showError = (message) => addToast(message, 'error');
  const showInfo = (message) => addToast(message, 'info');
  const showWarning = (message) => addToast(message, 'warning');

  return (
    <ToastContext.Provider value={{ showSuccess, showError, showInfo, showWarning, addToast }}>
      {children}
      <div className="toast-container">
        {toasts.map(toast => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function Toast({ message, type, onClose }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, 5000);

    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className={`toast toast-${type}`} onClick={onClose}>
      <span className="toast-message">{message}</span>
      <button className="toast-close" onClick={onClose}>×</button>
    </div>
  );
}

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) {
    // Fallback if ToastProvider is not in the tree
    return {
      showSuccess: (msg) => window.alert(msg),
      showError: (msg) => window.alert(msg),
      showInfo: (msg) => window.alert(msg),
      showWarning: (msg) => window.alert(msg),
    };
  }
  return context;
}

export default ToastProvider;

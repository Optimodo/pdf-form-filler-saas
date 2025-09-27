/**
 * User-friendly error message mapper
 * Maps technical error codes to human-readable messages
 */

const ERROR_MESSAGES = {
  // Authentication errors
  'LOGIN_BAD_CREDENTIALS': 'Invalid email or password. Please check your credentials and try again.',
  'LOGIN_USER_NOT_VERIFIED': 'Please verify your email address before signing in.',
  'REGISTER_USER_ALREADY_EXISTS': 'An account with this email already exists. Please sign in instead.',
  'RESET_PASSWORD_BAD_TOKEN': 'This password reset link is invalid or has expired. Please request a new one.',
  'VERIFY_USER_BAD_TOKEN': 'This verification link is invalid or has expired. Please request a new one.',
  'VERIFY_USER_ALREADY_VERIFIED': 'Your account is already verified.',
  
  // Password errors
  'UPDATE_USER_EMAIL_ALREADY_EXISTS': 'This email address is already in use by another account.',
  'UPDATE_USER_INVALID_PASSWORD': 'Current password is incorrect.',
  
  // General errors
  'UNAUTHORIZED': 'You need to be signed in to access this feature.',
  'FORBIDDEN': 'You don\'t have permission to perform this action.',
  'NOT_FOUND': 'The requested resource was not found.',
  'INTERNAL_SERVER_ERROR': 'Something went wrong on our end. Please try again later.',
  
  // File processing errors
  'FILE_TOO_LARGE': 'The selected file is too large. Please choose a smaller file.',
  'INVALID_FILE_TYPE': 'Invalid file type. Please select a supported file format.',
  'PROCESSING_FAILED': 'File processing failed. Please check your file and try again.',
  
  // Rate limiting
  'RATE_LIMIT_EXCEEDED': 'Too many requests. Please wait a moment before trying again.',
  
  // Default fallbacks
  'UNKNOWN_ERROR': 'An unexpected error occurred. Please try again or contact support if the problem persists.'
};

/**
 * Get user-friendly error message from error response
 * @param {string|object} error - Error message or error object
 * @returns {string} User-friendly error message
 */
export function getUserFriendlyError(error) {
  // Handle different error formats
  let errorCode = null;
  let errorMessage = null;

  if (typeof error === 'string') {
    errorCode = error;
  } else if (error?.detail) {
    errorCode = error.detail;
  } else if (error?.message) {
    errorMessage = error.message;
  } else if (error?.error) {
    errorCode = error.error;
  }

  // If we have a mapped error code, use it
  if (errorCode && ERROR_MESSAGES[errorCode]) {
    return ERROR_MESSAGES[errorCode];
  }

  // If we have a readable error message, use it
  if (errorMessage && !errorMessage.includes('_') && errorMessage.length > 5) {
    return errorMessage;
  }

  // Fallback for unmapped codes
  if (errorCode) {
    return ERROR_MESSAGES['UNKNOWN_ERROR'] + ` (Error: ${errorCode})`;
  }

  return ERROR_MESSAGES['UNKNOWN_ERROR'];
}

/**
 * Check if an error is a network/connection error
 * @param {Error} error - Error object
 * @returns {boolean}
 */
export function isNetworkError(error) {
  return error?.name === 'TypeError' && error?.message?.includes('fetch');
}

/**
 * Get appropriate error message for network issues
 * @returns {string}
 */
export function getNetworkErrorMessage() {
  return 'Unable to connect to the server. Please check your internet connection and try again.';
}

export default {
  getUserFriendlyError,
  isNetworkError,
  getNetworkErrorMessage,
  ERROR_MESSAGES
};

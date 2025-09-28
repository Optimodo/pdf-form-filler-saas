/**
 * API service for communicating with the backend
 */
import { getUserFriendlyError, isNetworkError, getNetworkErrorMessage } from '../utils/errorMessages';

const API_BASE_URL = 'http://localhost:8000';

class APIService {
  /**
   * Handle API response errors with user-friendly messages
   * @param {Response} response - Fetch response object
   * @param {string} defaultMessage - Default error message
   * @returns {Promise<Error>} - Processed error
   */
  async handleApiError(response, defaultMessage = 'Request failed') {
    try {
      const errorData = await response.json();
      const friendlyMessage = getUserFriendlyError(errorData);
      return new Error(friendlyMessage);
    } catch (parseError) {
      // If we can't parse the error response, use a friendly default
      return new Error(getUserFriendlyError(defaultMessage));
    }
  }

  /**
   * Handle network errors
   * @param {Error} error - Original error
   * @param {string} context - Context of the operation
   * @returns {Error} - Processed error
   */
  handleNetworkError(error, context = 'operation') {
    if (isNetworkError(error)) {
      return new Error(getNetworkErrorMessage());
    }
    return new Error(getUserFriendlyError(error.message || `Failed to complete ${context}`));
  }
  /**
   * Process PDFs using template and CSV data
   * @param {File} templateFile - PDF template file
   * @param {File} csvFile - CSV data file
   * @param {function} onProgress - Progress callback function
   * @returns {Promise} - API response
   */
  async processPDFs(templateFile, csvFile, onProgress = null) {
    try {
      const formData = new FormData();
      formData.append('template', templateFile);
      formData.append('csv_data', csvFile);
      
      const response = await fetch(`${API_BASE_URL}/api/pdf/process-batch`, {
        method: 'POST',
        headers: {
          ...this.getAuthHeaders(),
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result;
      
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  /**
   * Get real-time progress for a processing job
   * @param {string} jobId - Job ID from processing result
   * @returns {Promise} - Progress data
   */
  async getProgress(jobId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/pdf/progress/${encodeURIComponent(jobId)}`, {
        headers: {
          ...this.getAuthHeaders(),
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Progress API Error:', error);
      throw error;
    }
  }

  /**
   * Start processing with real-time progress updates
   * @param {File} templateFile - PDF template file
   * @param {File} csvFile - CSV data file
   * @param {function} onProgress - Progress callback function
   * @returns {Promise} - Final processing result
   */
  async processWithProgress(templateFile, csvFile, onProgress = null) {
    // Start processing (this will be async on backend)
    let jobId = null;
    let processingComplete = false;
    let finalResult = null;

    // Start the processing request
    const processingPromise = this.processPDFs(templateFile, csvFile).then(result => {
      finalResult = result;
      processingComplete = true;
      return result;
    });

    // Wait a moment for the job to be created
    await new Promise(resolve => setTimeout(resolve, 500));

    // For now, we'll use the promise approach since the processing is synchronous
    // In a real production app, you'd get the job_id immediately and poll for progress
    
    return processingPromise;
  }


  /**
   * Download a ZIP file containing all generated PDFs
   * @param {string} zipFilename - ZIP filename from processing result
   * @returns {Promise} - Download response
   */
  async downloadZIP(zipFilename) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/pdf/download-zip/${encodeURIComponent(zipFilename)}`,
        {
          headers: {
            ...this.getAuthHeaders(),
          },
        }
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // Create blob and download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = zipFilename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
    } catch (error) {
      console.error('ZIP Download Error:', error);
      throw error;
    }
  }

  /**
   * Health check endpoint
   * @returns {Promise} - Health status
   */
  async healthCheck() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      return await response.json();
    } catch (error) {
      console.error('Health Check Error:', error);
      throw error;
    }
  }

  // Authentication methods
  
  /**
   * Register a new user
   * @param {Object} userData - User registration data
   * @returns {Promise} - Registration response
   */
  async register(userData) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw await this.handleApiError(response, 'Registration failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Registration Error:', error);
      throw this.handleNetworkError(error, 'registration');
    }
  }

  /**
   * Login with email and password
   * @param {string} email - User email
   * @param {string} password - User password
   * @returns {Promise} - Login response with token
   */
  async login(email, password) {
    try {
      const formData = new FormData();
      formData.append('username', email); // FastAPI-Users expects 'username' field
      formData.append('password', password);

      const response = await fetch(`${API_BASE_URL}/api/auth/jwt/login`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw await this.handleApiError(response, 'Login failed');
      }

      const data = await response.json();
      
      // Store token in localStorage
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('token_type', data.token_type);
      
      return data;
    } catch (error) {
      console.error('Login Error:', error);
      throw this.handleNetworkError(error, 'login');
    }
  }

  /**
   * Logout user
   * @returns {Promise} - Logout response
   */
  async logout() {
    try {
      const token = localStorage.getItem('access_token');
      
      if (token) {
        await fetch(`${API_BASE_URL}/api/auth/jwt/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
      }
      
      // Clear stored tokens
      localStorage.removeItem('access_token');
      localStorage.removeItem('token_type');
      
    } catch (error) {
      console.error('Logout Error:', error);
      // Clear tokens even if API call fails
      localStorage.removeItem('access_token');
      localStorage.removeItem('token_type');
    }
  }

  /**
   * Get current user info
   * @returns {Promise} - Current user data
   */
  async getCurrentUser() {
    try {
      const token = localStorage.getItem('access_token');
      
      if (!token) {
        throw new Error('No authentication token found');
      }

      const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Token expired or invalid
          this.logout();
          throw new Error('Session expired');
        }
        throw new Error(`Failed to get user info: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Get Current User Error:', error);
      throw error;
    }
  }

  /**
   * Check if user is authenticated
   * @returns {boolean} - Authentication status
   */
  isAuthenticated() {
    const token = localStorage.getItem('access_token');
    return !!token;
  }

  /**
   * Get authorization header for API requests
   * @returns {Object} - Authorization headers
   */
  getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    console.log('Auth token:', token ? `${token.substring(0, 20)}...` : 'None');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  /**
   * Start Google OAuth flow
   * @returns {string} - Google OAuth URL
   */
  getGoogleOAuthUrl() {
    return `${API_BASE_URL}/api/auth/google/authorize`;
  }

  /**
   * Get current user's file size limits and restrictions
   * @returns {Promise} - User limits data
   */
  async getUserLimits() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/pdf/user-limits`, {
        headers: {
          ...this.getAuthHeaders(),
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to get user limits: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Get User Limits Error:', error);
      throw error;
    }
  }

  /**
   * Update user profile information
   * @param {Object} profileData - Profile data to update
   * @returns {Promise} - Updated user data
   */
  async updateProfile(profileData) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/users/me`, {
        method: 'PATCH',
        headers: {
          ...this.getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(profileData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to update profile: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Update Profile Error:', error);
      throw error;
    }
  }

  /**
   * Update user password using FastAPI-Users' built-in endpoint
   * @param {Object} passwordData - Password data
   * @returns {Promise} - Success response
   */
  async changePassword(passwordData) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/users/me`, {
        method: 'PATCH',
        headers: {
          ...this.getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ password: passwordData.new_password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw await this.handleApiError(response, 'Failed to update password');
      }

      return await response.json();
    } catch (error) {
      console.error('Update Password Error:', error);
      throw this.handleNetworkError(error, 'password update');
    }
  }

}

const apiService = new APIService();
export default apiService;

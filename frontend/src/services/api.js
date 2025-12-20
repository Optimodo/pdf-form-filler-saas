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

  // ==================== ADMIN API METHODS ====================

  /**
   * Check if current user is an admin
   * @returns {Promise<boolean>} - True if user is admin
   */
  async isAdmin() {
    try {
      const user = await this.getCurrentUser();
      return user.is_superuser === true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Get admin dashboard statistics
   * @returns {Promise} - Dashboard stats
   */
  async getAdminDashboardStats() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/dashboard/stats`, {
        headers: {
          ...this.getAuthHeaders(),
        },
      });

      if (!response.ok) {
        throw await this.handleApiError(response, 'Failed to get dashboard stats');
      }

      return await response.json();
    } catch (error) {
      console.error('Admin Dashboard Stats Error:', error);
      throw this.handleNetworkError(error, 'getting dashboard stats');
    }
  }

  /**
   * List users with pagination and filtering
   * @param {Object} params - Query parameters
   * @returns {Promise} - List of users
   */
  async listUsers(params = {}) {
    try {
      const queryParams = new URLSearchParams();
      if (params.skip !== undefined) queryParams.append('skip', params.skip);
      if (params.limit !== undefined) queryParams.append('limit', params.limit);
      if (params.search) queryParams.append('search', params.search);
      if (params.tier) queryParams.append('tier', params.tier);

      const url = `${API_BASE_URL}/api/admin/users${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
      const response = await fetch(url, {
        headers: {
          ...this.getAuthHeaders(),
        },
      });

      if (!response.ok) {
        throw await this.handleApiError(response, 'Failed to list users');
      }

      return await response.json();
    } catch (error) {
      console.error('List Users Error:', error);
      throw this.handleNetworkError(error, 'listing users');
    }
  }

  /**
   * Get detailed user information
   * @param {string} userId - User ID
   * @returns {Promise} - User details
   */
  async getUserDetails(userId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/users/${userId}`, {
        headers: {
          ...this.getAuthHeaders(),
        },
      });

      if (!response.ok) {
        throw await this.handleApiError(response, 'Failed to get user details');
      }

      return await response.json();
    } catch (error) {
      console.error('Get User Details Error:', error);
      throw this.handleNetworkError(error, 'getting user details');
    }
  }

  /**
   * Update user subscription tier
   * @param {string} userId - User ID
   * @param {string} tier - Subscription tier
   * @returns {Promise} - Update result
   */
  async updateUserSubscription(userId, tier) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/admin/users/${userId}/subscription?subscription_tier=${tier}`,
        {
          method: 'PATCH',
          headers: {
            ...this.getAuthHeaders(),
          },
        }
      );

      if (!response.ok) {
        throw await this.handleApiError(response, 'Failed to update subscription');
      }

      return await response.json();
    } catch (error) {
      console.error('Update Subscription Error:', error);
      throw this.handleNetworkError(error, 'updating subscription');
    }
  }

  /**
   * Set custom limits for a user
   * @param {string} userId - User ID
   * @param {Object} customLimits - Custom limits object
   * @param {string} reason - Reason for custom limits
   * @returns {Promise} - Update result
   */
  async setUserCustomLimits(userId, customLimits, reason) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/admin/users/${userId}/custom-limits?reason=${encodeURIComponent(reason)}`,
        {
          method: 'POST',
          headers: {
            ...this.getAuthHeaders(),
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(customLimits),
        }
      );

      if (!response.ok) {
        throw await this.handleApiError(response, 'Failed to set custom limits');
      }

      return await response.json();
    } catch (error) {
      console.error('Set Custom Limits Error:', error);
      throw this.handleNetworkError(error, 'setting custom limits');
    }
  }

  /**
   * Remove custom limits from a user
   * @param {string} userId - User ID
   * @returns {Promise} - Update result
   */
  async removeUserCustomLimits(userId) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/admin/users/${userId}/custom-limits`,
        {
          method: 'DELETE',
          headers: {
            ...this.getAuthHeaders(),
          },
        }
      );

      if (!response.ok) {
        throw await this.handleApiError(response, 'Failed to remove custom limits');
      }

      return await response.json();
    } catch (error) {
      console.error('Remove Custom Limits Error:', error);
      throw this.handleNetworkError(error, 'removing custom limits');
    }
  }

  /**
   * Apply a limit template to a user
   * @param {string} userId - User ID
   * @param {string} templateName - Template name
   * @param {string} reason - Optional reason
   * @returns {Promise} - Update result
   */
  async applyLimitTemplate(userId, templateName, reason = null) {
    try {
      const queryParams = new URLSearchParams({ template_name: templateName });
      if (reason) queryParams.append('reason', reason);

      const response = await fetch(
        `${API_BASE_URL}/api/admin/users/${userId}/apply-template?${queryParams.toString()}`,
        {
          method: 'POST',
          headers: {
            ...this.getAuthHeaders(),
          },
        }
      );

      if (!response.ok) {
        throw await this.handleApiError(response, 'Failed to apply template');
      }

      return await response.json();
    } catch (error) {
      console.error('Apply Template Error:', error);
      throw this.handleNetworkError(error, 'applying template');
    }
  }

  /**
   * Get available limit templates
   * @returns {Promise} - Available templates
   */
  async getAvailableTemplates() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/templates/available`, {
        headers: {
          ...this.getAuthHeaders(),
        },
      });

      if (!response.ok) {
        throw await this.handleApiError(response, 'Failed to get templates');
      }

      return await response.json();
    } catch (error) {
      console.error('Get Templates Error:', error);
      throw this.handleNetworkError(error, 'getting templates');
    }
  }

  /**
   * Toggle user active status
   * @param {string} userId - User ID
   * @param {boolean} isActive - Active status
   * @returns {Promise} - Update result
   */
  async toggleUserActive(userId, isActive) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/admin/users/${userId}/activate?is_active=${isActive}`,
        {
          method: 'PATCH',
          headers: {
            ...this.getAuthHeaders(),
          },
        }
      );

      if (!response.ok) {
        throw await this.handleApiError(response, 'Failed to update user status');
      }

      return await response.json();
    } catch (error) {
      console.error('Toggle User Active Error:', error);
      throw this.handleNetworkError(error, 'updating user status');
    }
  }

}

const apiService = new APIService();
export default apiService;

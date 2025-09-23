/**
 * API service for communicating with the backend
 */

const API_BASE_URL = 'http://localhost:8000';

class APIService {
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
   * Get list of available templates
   * @returns {Promise} - List of templates
   */
  async getTemplates() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/pdf/templates`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  /**
   * Download a ZIP file containing all generated PDFs
   * @param {string} zipFilename - ZIP filename from processing result
   * @returns {Promise} - Download response
   */
  async downloadZIP(zipFilename) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/pdf/download-zip/${encodeURIComponent(zipFilename)}`
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
}

const apiService = new APIService();
export default apiService;

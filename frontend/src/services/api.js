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
   * Get real-time progress for a processing job
   * @param {string} jobId - Job ID from processing result
   * @returns {Promise} - Progress data
   */
  async getProgress(jobId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/pdf/progress/${encodeURIComponent(jobId)}`);
      
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

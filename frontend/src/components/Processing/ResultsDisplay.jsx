import React from 'react';

const ResultsDisplay = ({ results, onDownloadZip }) => {
  if (!results || !results.success) {
    return null;
  }

  const { successful_count, total_count, generated_files, zip_file, errors } = results;

  return (
    <div className="results-container">
      <div className="results-summary">
        <h3>Processing Complete!</h3>
        <p>
          Successfully generated <strong>{successful_count}</strong> of <strong>{total_count}</strong> PDFs
        </p>
      </div>

      {/* Generated Files List */}
      {generated_files && generated_files.length > 0 && (
        <div className="generated-files">
          <h4>Generated Files ({generated_files.length} PDFs):</h4>
          <div className="file-preview">
            {generated_files.map((filename, index) => (
              <div key={index} className="file-preview-item">
                <span className="file-icon">📄</span>
                <span className="file-name">{filename}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ZIP Download Button */}
      {zip_file && (
        <div className="download-section">
          <button
            className="btn-download-zip"
            onClick={() => onDownloadZip(zip_file)}
          >
            📦 Download All PDFs as ZIP
          </button>
          <p className="download-info">
            Downloads {generated_files?.length || 0} PDFs in a single ZIP file
          </p>
        </div>
      )}

      {/* ZIP Creation Error */}
      {results.zip_error && (
        <div className="zip-error">
          <p className="error-text">
            ⚠️ Could not create ZIP file: {results.zip_error}
          </p>
          <p className="error-help">
            Please contact support if this issue persists.
          </p>
        </div>
      )}

      {/* Processing Errors */}
      {errors && errors.length > 0 && (
        <div className="errors-section">
          <h4>Processing Errors:</h4>
          <ul className="error-list">
            {errors.map((error, index) => (
              <li key={index} className="error-item">
                {error}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default ResultsDisplay;

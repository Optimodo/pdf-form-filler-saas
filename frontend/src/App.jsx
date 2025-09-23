import React, { useState } from 'react';
import Header from './components/Layout/Header';
import FileDropzone from './components/Upload/FileDropzone';
import ProgressBar from './components/Processing/ProgressBar';
import ResultsDisplay from './components/Processing/ResultsDisplay';
import AdBanner from './components/Ads/AdBanner';
import APIService from './services/api';
import './styles/themes.css';
import './styles/components.css';

function App() {
  const [pdfFile, setPdfFile] = useState(null);
  const [csvFile, setCsvFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('');
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handlePdfSelect = (file) => {
    setPdfFile(file);
    setResults(null); // Clear previous results
    setError(null);
  };

  const handleCsvSelect = (file) => {
    setCsvFile(file);
    setResults(null); // Clear previous results
    setError(null);
  };

  const handleGenerate = async () => {
    if (!pdfFile || !csvFile) {
      alert('Please select both PDF template and CSV data files');
      return;
    }

    setIsProcessing(true);
    setProgress(0);
    setStatus('Starting PDF generation...');
    setResults(null);
    setError(null);

    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 20, 90));
      }, 500);

      setStatus('Processing PDFs...');
      
      // Call the actual API
      const result = await APIService.processPDFs(pdfFile, csvFile);
      
      clearInterval(progressInterval);
      setProgress(100);
      setStatus('Complete!');
      setResults(result);
      
      setTimeout(() => {
        setIsProcessing(false);
      }, 1000);

    } catch (err) {
      setProgress(0);
      setStatus('');
      setError(err.message || 'An error occurred during processing');
      setIsProcessing(false);
    }
  };

  const handleDownloadZip = async (zipFilename) => {
    try {
      await APIService.downloadZIP(zipFilename);
    } catch (err) {
      alert(`ZIP download failed: ${err.message}`);
    }
  };

  const canGenerate = pdfFile && csvFile && !isProcessing;

  return (
    <div className="app">
      <Header />
      
      <main className="main-container">
        {/* Top Ad Banners */}
        <div className="ads-top">
          <AdBanner size="medium" position="top-left" />
          <AdBanner size="medium" position="top-right" />
        </div>

        {/* Main Upload Interface */}
        <div className="upload-section">
          <FileDropzone
            title="Drop PDF Template Here"
            icon="📄"
            acceptedTypes=".pdf"
            onFileSelect={handlePdfSelect}
            className="pdf-upload"
          />

          <FileDropzone
            title="Drop CSV Data Here"
            icon="📊"
            acceptedTypes=".csv"
            onFileSelect={handleCsvSelect}
            className="csv-upload"
          />

          <div className="output-section">
            <div className="file-dropzone output-location">
              <div className="dropzone-content">
                <div className="dropzone-icon">📁</div>
                <div className="dropzone-text">
                  <div className="primary-text">Output Location (Optional)</div>
                  <div className="secondary-text">Downloads folder by default</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Generate Button */}
        <div style={{ textAlign: 'center' }}>
          <button 
            className="btn-primary"
            onClick={handleGenerate}
            disabled={!canGenerate}
          >
            {isProcessing ? 'Generating PDFs...' : 'Generate PDFs'}
          </button>
        </div>

        {/* Progress Bar */}
        <ProgressBar 
          progress={progress}
          status={status}
          isVisible={isProcessing || progress === 100}
        />

        {/* Error Message */}
        {error && (
          <div className="status-message status-error">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Results Display */}
        <ResultsDisplay 
          results={results}
          onDownloadZip={handleDownloadZip}
        />

        {/* Bottom Ad Banners */}
        <div className="ads-bottom">
          <AdBanner size="medium" position="bottom-left" />
          <AdBanner size="medium" position="bottom-right" />
        </div>
      </main>
    </div>
  );
}

export default App;

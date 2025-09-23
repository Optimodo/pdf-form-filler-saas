import React, { useState, useEffect } from 'react';
import { AuthProvider } from './contexts/AuthContext';
import Header from './components/Layout/Header';
import FileDropzone from './components/Upload/FileDropzone';
import ProgressBar from './components/Processing/ProgressBar';
import ResultsDisplay from './components/Processing/ResultsDisplay';
import AdBanner from './components/Ads/AdBanner';
import GoogleCallback from './components/Auth/GoogleCallback';
import APIService from './services/api';
import './styles/themes.css';
import './styles/components.css';

function App() {
  const [currentRoute, setCurrentRoute] = useState('/');
  const [pdfFile, setPdfFile] = useState(null);
  const [csvFile, setCsvFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('');
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  // Simple routing based on URL path
  useEffect(() => {
    const path = window.location.pathname;
    setCurrentRoute(path);
    
    // Listen for route changes
    const handlePopState = () => {
      setCurrentRoute(window.location.pathname);
    };
    
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

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
      setStatus('Calculating...');
      setProgress(5);
      
      // Get file count first
      const fileCount = await estimateFileCount(csvFile);
      
      if (fileCount > 0) {
        setStatus(`Processing ${fileCount} PDFs...`);
        
        // Start processing
        const startTime = Date.now();
        let currentFile = 0;
        let timePerFile = 0.1; // Start with optimistic estimate (100ms per file)
        let adaptiveEstimate = false;
        
        // Progress update that gets smarter over time
        const progressInterval = setInterval(() => {
          const elapsed = (Date.now() - startTime) / 1000;
          
          // For first few seconds, show initial progress
          if (elapsed < 3) {
            const initialProgress = Math.min((elapsed / 3) * 20, 20); // 20% in first 3 seconds
            setProgress(5 + initialProgress);
            setStatus(`Processing ${fileCount} PDFs...`);
          } else {
            // After initial loading, simulate file-by-file processing
            const processingTime = elapsed - 3; // Subtract initial loading time
            
            // Adaptive estimation: After 5-8 seconds of processing, calculate real average
            if (processingTime > 5 && !adaptiveEstimate && fileCount >= 5) {
              // We've been processing for 5+ seconds, calculate actual rate
              const estimatedFilesProcessedSoFar = Math.floor(processingTime / timePerFile);
              if (estimatedFilesProcessedSoFar >= 5) {
                // Calculate actual time per file based on real progress
                const realTimePerFile = processingTime / estimatedFilesProcessedSoFar;
                timePerFile = realTimePerFile;
                adaptiveEstimate = true;
                console.log(`Adaptive estimate: ${(realTimePerFile * 1000).toFixed(0)}ms per file (was ${100}ms)`);
              }
            }
            
            const estimatedFilesProcessed = Math.floor(processingTime / timePerFile);
            currentFile = Math.min(estimatedFilesProcessed, fileCount);
            
            const progressPercent = Math.min(25 + (currentFile / fileCount) * 65, 90); // 25% to 90%
            setProgress(progressPercent);
            
            if (currentFile < fileCount) {
              const remainingFiles = fileCount - currentFile;
              const estimatedRemainingTime = remainingFiles * timePerFile;
              
              const timeLabel = adaptiveEstimate ? '' : '~'; // Remove ~ once we have real data
              
              if (estimatedRemainingTime > 60) {
                setStatus(`Processing file ${currentFile + 1} of ${fileCount}... ${timeLabel}${Math.ceil(estimatedRemainingTime / 60)} min remaining`);
              } else {
                setStatus(`Processing file ${currentFile + 1} of ${fileCount}... ${timeLabel}${Math.ceil(estimatedRemainingTime)}s remaining`);
              }
            } else {
              setStatus('Creating ZIP file...');
            }
          }
        }, 500); // Update every 500ms for smoother progress
        
        // Call the actual API
        const result = await APIService.processPDFs(pdfFile, csvFile);
        
        clearInterval(progressInterval);
        setProgress(100);
        setStatus('Complete!');
        setResults(result);
        
        // Log actual time for future calibration
        const actualTime = (Date.now() - startTime) / 1000;
        console.log(`Actual processing time: ${actualTime}s for ${fileCount} files (${(actualTime/fileCount).toFixed(2)}s per file)`);
        
      } else {
        // Fallback for unknown file count
        setStatus('Processing PDFs...');
        const result = await APIService.processPDFs(pdfFile, csvFile);
        setProgress(100);
        setStatus('Complete!');
        setResults(result);
      }
      
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

  // Helper function to estimate file count from CSV
  const estimateFileCount = async (csvFile) => {
    try {
      const text = await csvFile.text();
      const lines = text.split('\n').filter(line => line.trim().length > 0);
      // Subtract 1 for header row, ensure minimum of 0
      return Math.max(lines.length - 1, 0);
    } catch (error) {
      console.warn('Could not estimate file count:', error);
      return 0;
    }
  };

  const canGenerate = pdfFile && csvFile && !isProcessing;

  // Handle Google OAuth callback route
  if (currentRoute.startsWith('/auth/google/callback')) {
    return (
      <AuthProvider>
        <div className="app">
          <Header />
          <main className="main-container">
            <GoogleCallback />
          </main>
        </div>
      </AuthProvider>
    );
  }

  // Main application route
  return (
    <AuthProvider>
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
                    fileType="pdf"
                  />

                  <FileDropzone
                    title="Drop CSV Data Here"
                    icon="📊"
                    acceptedTypes=".csv"
                    onFileSelect={handleCsvSelect}
                    className="csv-upload"
                    fileType="csv"
                  />
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
    </AuthProvider>
  );
}

export default App;

import React, { useState, useEffect } from 'react';
import { AuthProvider } from './contexts/AuthContext';
import Header from './components/Layout/Header';
import FileDropzone from './components/Upload/FileDropzone';
import ProgressBar from './components/Processing/ProgressBar';
import ResultsDisplay from './components/Processing/ResultsDisplay';
import AdBanner from './components/Ads/AdBanner';
import GoogleCallback from './components/Auth/GoogleCallback';
import UserDashboard from './components/Dashboard/UserDashboard';
import ProfileEdit from './components/Dashboard/ProfileEdit';
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

  const validateFilename = (filename) => {
    // Check if filename is too long (considering our prefix will add ~30 chars)
    const maxLength = 120; // Leave room for date, time, user ID prefix
    if (filename.length > maxLength) {
      return {
        isValid: false,
        message: `Filename too long (${filename.length} chars). Please keep under ${maxLength} characters to avoid filesystem limitations.`,
        suggestion: `Try shortening your filename to under ${maxLength} characters.`
      };
    }
    
    // Check for dangerous characters that could cause security issues
    const dangerousChars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|'];
    for (const char of dangerousChars) {
      if (filename.includes(char)) {
        return {
          isValid: false,
          message: `Filename contains invalid character: "${char}". Please use only letters, numbers, hyphens, and underscores.`,
          suggestion: `Remove the "${char}" character and use only letters, numbers, hyphens (-), and underscores (_).`
        };
      }
    }
    
    // Check for empty filename
    if (!filename.trim()) {
      return {
        isValid: false,
        message: "Filename cannot be empty.",
        suggestion: "Please choose a descriptive name for your file."
      };
    }
    
    // Check for reserved Windows names
    const reservedNames = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                          'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 
                          'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'];
    const nameWithoutExt = filename.split('.')[0].toUpperCase();
    if (reservedNames.includes(nameWithoutExt)) {
      return {
        isValid: false,
        message: `Filename "${nameWithoutExt}" is reserved by the system. Please choose a different name.`,
        suggestion: `Try adding a prefix like "my_${nameWithoutExt}" or use a completely different name.`
      };
    }
    
    return { isValid: true };
  };

  const handlePdfSelect = (file) => {
    const validation = validateFilename(file.name);
    if (!validation.isValid) {
      const errorMessage = validation.suggestion 
        ? `${validation.message}\n\n💡 Suggestion: ${validation.suggestion}`
        : validation.message;
      setError(errorMessage);
      return;
    }
    
    setPdfFile(file);
    setResults(null); // Clear previous results
    setError(null);
  };

  const handleCsvSelect = (file) => {
    const validation = validateFilename(file.name);
    if (!validation.isValid) {
      const errorMessage = validation.suggestion 
        ? `${validation.message}\n\n💡 Suggestion: ${validation.suggestion}`
        : validation.message;
      setError(errorMessage);
      return;
    }
    
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

  // Handle Dashboard route
  if (currentRoute === '/dashboard') {
    return (
      <AuthProvider>
        <div className="app">
          <Header />
          <main className="main-container">
            <UserDashboard />
          </main>
        </div>
      </AuthProvider>
    );
  }

  // Handle Profile Edit route
  if (currentRoute === '/profile') {
    return (
      <AuthProvider>
        <div className="app">
          <Header />
          <main className="main-container">
            <ProfileEdit />
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
            <strong>Error:</strong> 
            <div style={{ whiteSpace: 'pre-line', marginTop: '8px' }}>
              {error}
            </div>
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

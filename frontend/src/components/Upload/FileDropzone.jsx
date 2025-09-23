import React, { useState, useCallback } from 'react';

const FileDropzone = ({ 
  title, 
  icon, 
  acceptedTypes, 
  onFileSelect, 
  className = '' 
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      const file = files[0];
      setSelectedFile(file);
      onFileSelect(file);
    }
  }, [onFileSelect]);

  const handleFileInputChange = useCallback((e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      onFileSelect(file);
    }
  }, [onFileSelect]);

  const handleClick = () => {
    document.getElementById(`file-input-${title.replace(/\s+/g, '-')}`).click();
  };

  return (
    <div 
      className={`file-dropzone ${className} ${isDragOver ? 'drag-over' : ''} ${selectedFile ? 'has-file' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <div className="dropzone-content">
        <div className="dropzone-icon">{icon}</div>
        <div className="dropzone-text">
          {selectedFile ? (
            <div className="file-selected">
              <div className="file-name">{selectedFile.name}</div>
              <div className="file-size">{(selectedFile.size / 1024).toFixed(1)} KB</div>
            </div>
          ) : (
            <div className="file-prompt">
              <div className="primary-text">{title}</div>
              <div className="secondary-text">or click to browse</div>
            </div>
          )}
        </div>
      </div>
      
      <input
        id={`file-input-${title.replace(/\s+/g, '-')}`}
        type="file"
        accept={acceptedTypes}
        onChange={handleFileInputChange}
        style={{ display: 'none' }}
      />
    </div>
  );
};

export default FileDropzone;

import React, { useState, useMemo, useEffect } from 'react';
import { open } from "@tauri-apps/plugin-dialog";
import { scanPath } from '../../services/api.js';

const StepFile = ({ onPathSelect, onUpload, selectedPath, onConflictStrategyChange, conflictStrategy = 'overwrite', ignorePatterns = '', onIgnorePatternsChange }) => {
  const [pathError, setPathError] = useState('');
  const [confirmLargeFiles, setConfirmLargeFiles] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [scanError, setScanError] = useState('');
  
  const fileStats = useMemo(() => {
    if (!selectedPath) {
      return { count: 0, size: 0, sizeFormatted: '0 B' };
    }
    
    const paths = Array.isArray(selectedPath) ? selectedPath : [selectedPath];
    return {
      count: paths.length,
      size: 0,
      sizeFormatted: 'Scanning...'
    };
  }, [selectedPath]);
  
  const [realFileStats, setRealFileStats] = useState(fileStats);
  
  useEffect(() => {
    if (selectedPath) {
      performScan();
    } else {
      setRealFileStats({ count: 0, size: 0, sizeFormatted: '0 B' });
      setScanError('');
    }
  }, [selectedPath]);
  
  const performScan = async () => {
    if (!selectedPath) return;
    
    setIsScanning(true);
    setScanError('');
    
    try {
      const result = await scanPath(selectedPath);
      
      if (result.success) {
        const sizeBytes = result.size || 0;
        let sizeFormatted;
        
        if (sizeBytes < 1024) {
          sizeFormatted = `${sizeBytes} B`;
        } else if (sizeBytes < 1024 * 1024) {
          sizeFormatted = `${(sizeBytes / 1024).toFixed(2)} KB`;
        } else if (sizeBytes < 1024 * 1024 * 1024) {
          sizeFormatted = `${(sizeBytes / 1024 / 1024).toFixed(2)} MB`;
        } else {
          sizeFormatted = `${(sizeBytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
        }
        
        setRealFileStats({
          count: result.count || 0,
          size: sizeBytes,
          sizeFormatted
        });
      } else {
        setScanError(result.message || 'Failed to scan path');
        setRealFileStats({
          count: 0,
          size: 0,
          sizeFormatted: '0 B'
        });
      }
    } catch (error) {
      setScanError(error.message || 'Failed to scan path');
      setRealFileStats({
        count: 0,
        size: 0,
        sizeFormatted: '0 B'
      });
    } finally {
      setIsScanning(false);
    }
  };
  
  const MAX_SIZE = 50 * 1024 * 1024;
  const exceedsSizeLimit = realFileStats.size > MAX_SIZE;

  const handleChooseFile = async () => {
    try {
      const selected = await open({
        multiple: true,
        directory: false,
        title: 'Choose Files to Upload'
      });
      
      if (selected) {
        console.log("UPLOAD_DEBUG_PATH =", selected);
        onPathSelect(selected);
        setConfirmLargeFiles(false);
      }
    } catch (error) {
      console.error('Error selecting file:', error);
    }
  };

  const handleChooseFolder = async () => {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: 'Choose Folder to Upload'
      });
      
      if (selected) {
        console.log("UPLOAD_DEBUG_PATH =", selected);
        onPathSelect(selected);
        setConfirmLargeFiles(false);
      }
    } catch (error) {
      console.error('Error selecting folder:', error);
    }
  };
  
  const handleRemovePath = (index) => {
    if (!Array.isArray(selectedPath)) return;
    
    const newPaths = selectedPath.filter((_, i) => i !== index);
    onPathSelect(newPaths.length > 0 ? newPaths : null);
    setConfirmLargeFiles(false);
  };
  
  const handleConflictStrategyChange = (e) => {
    onConflictStrategyChange(e.target.value);
  };

  return (
    <div className="step-content">
      <h3 className="step-title">Step 4: Select File or Folder</h3>
      <p className="step-description">
        Choose the file(s), folder, or zip you want to upload to GitHub.
      </p>
      
      <div className="action-card">
        <div className="file-selector-buttons">
          <button 
            type="button" 
            className="btn-secondary" 
            onClick={handleChooseFile}
            disabled={isScanning}
          >
            📁 Choose Files
          </button>
          
          <button 
            type="button" 
            className="btn-secondary" 
            onClick={handleChooseFolder}
            style={{ marginLeft: '12px' }}
            disabled={isScanning}
          >
            📂 Choose Folder
          </button>
        </div>
       
        {selectedPath && (
          <div className="selected-path" style={{ marginTop: '16px' }}>
            <div className="selected-path-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div className="selected-path-label">Selected Path(s):</div>
              <div className="file-stats" style={{ fontSize: '12px', color: '#666' }}>
                {isScanning ? (
                  <span>Scanning... ⏳</span>
                ) : scanError ? (
                  <span style={{ color: '#dc3545' }}>Error: {scanError}</span>
                ) : (
                  <span>{realFileStats.count} items, Total {realFileStats.sizeFormatted}</span>
                )}
              </div>
            </div>
            
            {Array.isArray(selectedPath) ? (
              <ul style={{ margin: 0, paddingLeft: '0', listStyle: 'none' }}>
                {selectedPath.map((path, index) => (
                  <li key={index} style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    padding: '8px',
                    marginBottom: '8px',
                    backgroundColor: '#f5f5f5',
                    borderRadius: '4px'
                  }}>
                    <span>{path}</span>
                    <button 
                      type="button" 
                      className="btn-small" 
                      onClick={() => handleRemovePath(index)}
                      disabled={isScanning}
                      style={{ 
                        backgroundColor: '#ff6b6b',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '4px 8px',
                        cursor: isScanning ? 'not-allowed' : 'pointer',
                        fontSize: '12px',
                        opacity: isScanning ? 0.5 : 1
                      }}
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <div style={{ 
                padding: '8px',
                backgroundColor: '#f5f5f5',
                borderRadius: '4px',
                marginBottom: '8px'
              }}>
                {selectedPath}
              </div>
            )}
            
            {scanError && (
              <div className="error-message" style={{ marginTop: '8px', padding: '8px', backgroundColor: '#f8d7da', borderRadius: '4px', color: '#721c24' }}>
                {scanError}
              </div>
            )}
            
            <div className="conflict-strategy" style={{ marginTop: '16px' }}>
              <label className="form-label" style={{ display: 'block', marginBottom: '8px' }}>
                File Conflict Strategy:
              </label>
              <select
                className="form-control"
                value={conflictStrategy}
                onChange={handleConflictStrategyChange}
                disabled={isScanning}
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
              >
                <option value="overwrite">Overwrite existing files</option>
                <option value="skip">Skip existing files</option>
                <option value="rename">Rename new files</option>
              </select>
            </div>

            <div className="ignore-patterns" style={{ marginTop: '16px' }}>
              <label className="form-label" style={{ display: 'block', marginBottom: '8px' }}>
                Ignore patterns (one per line):
              </label>
              <textarea
                className="form-control"
                value={ignorePatterns}
                onChange={(e) => onIgnorePatternsChange && onIgnorePatternsChange(e.target.value)}
                rows={4}
                disabled={isScanning}
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                placeholder=".git&#10;node_modules&#10;dist&#10;*.log"
              />
              <p className="form-hint" style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                Gitignore-style globs; defaults skip .git, node_modules, dist, logs, tmp, .DS_Store.
              </p>
            </div>
          </div>
        )}
        
        {!selectedPath && (
          <div className="empty-state" style={{ marginTop: '16px' }}>
            <p>Click the buttons above to select files or a folder.</p>
          </div>
        )}

        {pathError && (
          <div className="error-message" style={{ marginTop: '12px' }}>
            {pathError}
          </div>
        )}
        
        {exceedsSizeLimit && !confirmLargeFiles && (
          <div className="warning-message" style={{ marginTop: '12px', padding: '8px', backgroundColor: '#fff3cd', borderRadius: '4px', color: '#856404' }}>
            <p>Warning: Total file size is {realFileStats.sizeFormatted}, exceeding the recommended limit of 50MB.</p>
            <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
              <button 
                type="button" 
                className="btn-secondary" 
                onClick={() => setConfirmLargeFiles(true)}
                disabled={isScanning}
              >
                Continue Upload
              </button>
              <button 
                type="button" 
                className="btn-secondary" 
                onClick={() => setPathError('Please select smaller files or folders')}
                disabled={isScanning}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
      
      <div className="step-navigation">
        <button 
          type="button" 
          className="btn-primary" 
          onClick={async () => {
            setPathError('');
            if (!selectedPath) {
              setPathError('Please select file or folder first');
              return;
            }
            
            if (isScanning) {
              setPathError('Please wait for scanning to complete');
              return;
            }
            
            if (scanError) {
              setPathError('Cannot upload due to scan error');
              return;
            }
            
            if (exceedsSizeLimit && !confirmLargeFiles) {
              setPathError('Please confirm large file upload');
              return;
            }
            
            onUpload(selectedPath);
          }}
          disabled={!selectedPath || isScanning || scanError || (exceedsSizeLimit && !confirmLargeFiles)}
        >
          Upload to GitHub →
        </button>
      </div>
    </div>
  );
};

export default StepFile;

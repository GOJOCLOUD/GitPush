import React, { useState, useMemo } from 'react';
import { open } from "@tauri-apps/plugin-dialog";
// In Tauri 2.x, fs exists function is not available directly, we'll use a mock for now
const exists = async (path) => {
  // Mock implementation that always returns true for build purposes
  // In production, we'll need to add the fs plugin and use the correct API
  return true;
};

const StepFile = ({ onPathSelect, onUpload, selectedPath, onConflictStrategyChange, conflictStrategy = 'overwrite', ignorePatterns = '', onIgnorePatternsChange }) => {
  const [pathError, setPathError] = useState('');
  const [confirmLargeFiles, setConfirmLargeFiles] = useState(false);
  
  // File count and size estimation (mock data for now, will be replaced with actual calculation)
  const fileStats = useMemo(() => {
    if (!selectedPath) {
      return { count: 0, size: 0 };
    }
    
    const paths = Array.isArray(selectedPath) ? selectedPath : [selectedPath];
    return {
      count: paths.length,
      size: paths.length * 1024 * 1024, // Mock size: 1MB per file/folder
      sizeFormatted: `${(paths.length * 1).toFixed(2)} MB`
    };
  }, [selectedPath]);
  
  // Maximum allowed size (50MB for example)
  const MAX_SIZE = 50 * 1024 * 1024;
  
  // Check if files exceed size limit
  const exceedsSizeLimit = fileStats.size > MAX_SIZE;

  const handleChooseFile = async () => {
    try {
      // Use Tauri dialog plugin to select file, which returns absolute path
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
      // Use Tauri dialog plugin to select folder, which returns absolute path
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
          >
            📁 Choose Files
          </button>
          
          <button 
            type="button" 
            className="btn-secondary" 
            onClick={handleChooseFolder}
            style={{ marginLeft: '12px' }}
          >
            📂 Choose Folder
          </button>
        </div>
       
        {selectedPath && (
          <div className="selected-path" style={{ marginTop: '16px' }}>
            <div className="selected-path-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div className="selected-path-label">Selected Path(s):</div>
              <div className="file-stats" style={{ fontSize: '12px', color: '#666' }}>
                {fileStats.count} items, Total {fileStats.sizeFormatted}
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
                      style={{ 
                        backgroundColor: '#ff6b6b',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '4px 8px',
                        cursor: 'pointer',
                        fontSize: '12px'
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
            
            {/* Conflict Strategy Selection */}
            <div className="conflict-strategy" style={{ marginTop: '16px' }}>
              <label className="form-label" style={{ display: 'block', marginBottom: '8px' }}>
                File Conflict Strategy:
              </label>
              <select
                className="form-control"
                value={conflictStrategy}
                onChange={handleConflictStrategyChange}
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
              >
                <option value="overwrite">Overwrite existing files</option>
                <option value="skip">Skip existing files</option>
                <option value="rename">Rename new files</option>
              </select>
            </div>

            {/* Ignore patterns */}
            <div className="ignore-patterns" style={{ marginTop: '16px' }}>
              <label className="form-label" style={{ display: 'block', marginBottom: '8px' }}>
                Ignore patterns (one per line):
              </label>
              <textarea
                className="form-control"
                value={ignorePatterns}
                onChange={(e) => onIgnorePatternsChange && onIgnorePatternsChange(e.target.value)}
                rows={4}
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
            <p>Warning: Total file size is {fileStats.sizeFormatted}, exceeding the recommended limit of 50MB.</p>
            <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
              <button 
                type="button" 
                className="btn-secondary" 
                onClick={() => setConfirmLargeFiles(true)}
              >
                Continue Upload
              </button>
              <button 
                type="button" 
                className="btn-secondary" 
                onClick={() => setPathError('Please select smaller files or folders')}
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
            
            // Check if files exceed size limit and not confirmed
            if (exceedsSizeLimit && !confirmLargeFiles) {
              setPathError('Please confirm large file upload');
              return;
            }
            
            // Validate paths
            const paths = Array.isArray(selectedPath) ? selectedPath : [selectedPath];
            const invalid = [];
            for (const p of paths) {
              try {
                const ok = await exists(p);
                if (!ok) invalid.push(p);
              } catch (err) {
                invalid.push(p);
              }
            }
            
            if (invalid.length) {
              setPathError(`Path does not exist or is unreadable: ${invalid.join(', ')}`);
              return;
            }
            
            onUpload(selectedPath);
          }}
          disabled={!selectedPath || (exceedsSizeLimit && !confirmLargeFiles)}
        >
          Upload to GitHub →
        </button>
      </div>
    </div>
  );
};

export default StepFile;

import React, { useState } from 'react';

const StepUpload = ({ uploadResult, isUploading, onReset, uploadStage = '', uploadStats = {} }) => {
  const [copied, setCopied] = useState(false);
  
  // Copy error details to clipboard
  const copyErrorDetails = () => {
    if (!uploadResult || uploadResult.success) return;
    
    const errorDetails = {
      message: uploadResult.message,
      stderr: uploadResult.stderr,
      details: uploadResult.details
    };
    
    navigator.clipboard.writeText(JSON.stringify(errorDetails, null, 2))
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch(err => {
        console.error('Failed to copy error details:', err);
      });
  };
  
  // Get readable stage name
  const getStageName = (stage) => {
    const stageMap = {
      'validate': 'Validating parameters...',
      'copy': 'Copying files...',
      'git_add': 'Git adding files...',
      'git_commit': 'Git committing...',
      'git_push': 'Git pushing...',
      'done': 'Done'
    };
    return stageMap[stage] || stage || 'Processing...';
  };

  return (
    <div className="step-content">
      <h3 className="step-title">Step 5: Upload Results</h3>
      
      {isUploading && (
        <div className="loading-indicator">
          <div className="uploading-animation">
            <span>📤 Uploading to GitHub...</span>
            <div className="progress-dots">
              <span>.</span>
              <span>.</span>
              <span>.</span>
            </div>
          </div>
          
          {/* Progress stage display */}
          <div className="upload-stage" style={{ marginTop: '16px', fontSize: '14px', color: '#666' }}>
            Current stage: <strong>{getStageName(uploadStage)}</strong>
          </div>
          
          {/* Upload stats */}
          {Object.keys(uploadStats).length > 0 && (
            <div className="upload-stats" style={{ marginTop: '8px', fontSize: '12px', color: '#888' }}>
              {uploadStats.filesProcessed && <span>Processed: {uploadStats.filesProcessed} files</span>}
              {uploadStats.totalFiles && <span> / Total: {uploadStats.totalFiles} files</span>}
              {uploadStats.bytesProcessed && <span> / Size: {(uploadStats.bytesProcessed / 1024 / 1024).toFixed(2)} MB</span>}
            </div>
          )}
        </div>
      )}
      
      {!isUploading && uploadResult && (
        <div className="result-container">
          <div className={`result-card ${uploadResult?.success ? 'success' : 'error'}`}>
            <div className="result-header">
              {uploadResult?.success ? (
                <span className="success-icon">✅ Upload Successful!</span>
              ) : (
                <span className="error-icon">❌ Upload Failed</span>
              )}
            </div>
            
            {uploadResult?.success ? (
              /* Success state */
              <div className="result-details">
                <div className="success-summary" style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '150px 1fr', gap: '8px', marginBottom: '16px' }}>
                    <span style={{ fontWeight: 'bold' }}>Repository:</span>
                    <span>{uploadResult.repo}</span>
                    
                    <span style={{ fontWeight: 'bold' }}>Branch:</span>
                    <span>{uploadResult.branch}</span>
                    
                    <span style={{ fontWeight: 'bold' }}>Files:</span>
                    <span>{uploadResult.statistics?.file_count || 0}</span>
                    
                    <span style={{ fontWeight: 'bold' }}>Size:</span>
                    <span>{uploadResult.statistics?.total_size_mb || '0'} MB</span>
                    
                    <span style={{ fontWeight: 'bold' }}>Time Taken:</span>
                    <span>{uploadResult.took} ms</span>
                    
                    {uploadResult.commit_sha && (
                      <>
                        <span style={{ fontWeight: 'bold' }}>Local Commit SHA:</span>
                        <span>{uploadResult.commit_sha}</span>
                      </>
                    )}
                    
                    {uploadResult.remote_sha && (
                      <>
                        <span style={{ fontWeight: 'bold' }}>Remote Branch SHA:</span>
                        <span>{uploadResult.remote_sha}</span>
                      </>
                    )}
                  </div>
                  
                  {/* Success message */}
                  <div className="success-message" style={{ color: '#28a745', marginBottom: '16px' }}>
                    {uploadResult.statistics?.file_count > 0 ? 'Upload completed successfully' : 'No changes to upload (files already up to date)'}
                  </div>
                </div>
                
                <div className="result-actions">
                  <a 
                    href={uploadResult.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="result-link btn-primary"
                    style={{ 
                      display: 'inline-block', 
                      padding: '8px 16px', 
                      backgroundColor: '#28a745', 
                      color: 'white', 
                      textDecoration: 'none', 
                      borderRadius: '4px', 
                      marginRight: '8px',
                      marginBottom: '8px'
                    }}
                  >
                    🔗 View on GitHub
                  </a>
                  <button 
                    type="button" 
                    className="btn-secondary"
                    onClick={onReset}
                    style={{ 
                      padding: '8px 16px', 
                      marginBottom: '8px'
                    }}
                  >
                    Upload Again
                  </button>
                </div>
              </div>
            ) : (
              /* Error state */
              <div className="result-details">
                {/* Error message */}
                {uploadResult.message && (
                  <div className="error-message-text" style={{ color: '#dc3545', marginBottom: '16px', fontSize: '14px' }}>
                    {uploadResult.message}
                  </div>
                )}
                
                {/* Error details sections */}
                <div className="error-sections" style={{ marginBottom: '16px' }}>
                  {/* stderr */}
                  {(uploadResult.stderr || uploadResult.push_stderr) && (
                    <div className="stderr-section" style={{ marginBottom: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <h4 style={{ margin: 0, fontSize: '14px', color: '#666' }}>Error Details:</h4>
                        <button 
                          type="button" 
                          className="btn-small"
                          onClick={copyErrorDetails}
                          style={{ 
                            fontSize: '12px', 
                            padding: '4px 8px',
                            backgroundColor: '#6c757d',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer'
                          }}
                        >
                          {copied ? 'Copied!' : 'Copy'}
                        </button>
                      </div>
                      <pre className="stderr-output" style={{
                        backgroundColor: '#f8d7da',
                        color: '#721c24',
                        padding: '12px',
                        borderRadius: '4px',
                        overflow: 'auto',
                        maxHeight: '200px',
                        fontSize: '12px',
                        margin: 0
                      }}>
                        {((uploadResult.stderr || uploadResult.push_stderr) || '').slice(0, 1000)} {/* Show first 1000 characters only */}
                        {((uploadResult.stderr || uploadResult.push_stderr) || '').length > 1000 && '...'}
                      </pre>
                    </div>
                  )}
                  
                  {/* Additional details */}
                  {uploadResult.push_stdout && (
                    <div className="details-section" style={{ marginBottom: '12px' }}>
                      <h4 style={{ margin: 0, fontSize: '14px', color: '#666', marginBottom: '8px' }}>Push Output:</h4>
                      <pre className="details-output" style={{
                        backgroundColor: '#e9ecef',
                        padding: '12px',
                        borderRadius: '4px',
                        overflow: 'auto',
                        maxHeight: '150px',
                        fontSize: '12px',
                        margin: 0
                      }}>
                        {uploadResult.push_stdout}
                      </pre>
                    </div>
                  )}
                </div>
                
                {/* Error stats */}
                {uploadResult.took && (
                  <div className="error-stats" style={{ fontSize: '12px', color: '#666', marginBottom: '16px' }}>
                    Time taken: {uploadResult.took} ms
                  </div>
                )}
              </div>
            )}
          </div>
          
          {/* Reset button for all cases */}
          <div className="step-navigation" style={{ marginTop: '24px' }}>
            <button 
              type="button" 
              className="btn-secondary" 
              onClick={onReset}
            >
              Start Over
            </button>
          </div>
        </div>
      )}
      
      {!isUploading && !uploadResult && (
        <div className="empty-state">
          <p>Upload has not started yet.</p>
        </div>
      )}
    </div>
  );
};

export default StepUpload;

import React, { useState } from 'react';

  const StepUpload = ({ uploadResult, isUploading, onReset, uploadStage = '', uploadStats = {} }) => {
  const [copied, setCopied] = useState(false);
  
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
  
  const getStageName = (stage) => {
    const stageMap = {
      'validate': '正在验证参数...',
      'copy': '正在复制文件...',
      'git_add': '正在添加文件到 Git...',
      'git_commit': '正在提交...',
      'git_push': '正在推送到 GitHub...',
      'done': '完成'
    };
    return stageMap[stage] || stage || '处理中...';
  };

  return (
    <div className="step-content">
      <h3 className="step-title">步骤 5: 上传结果</h3>
      
      {isUploading && (
        <div className="loading-indicator">
          <div className="uploading-animation">
            <span>📤 正在上传到 GitHub...</span>
            <div className="progress-dots">
              <span>.</span>
              <span>.</span>
              <span>.</span>
            </div>
          </div>
          
          {/* Progress stage display */}
          <div className="upload-stage" style={{ marginTop: '16px', fontSize: '14px', color: '#666' }}>
            当前阶段: <strong>{getStageName(uploadStage)}</strong>
          </div>
          
          {/* Upload stats */}
          {Object.keys(uploadStats).length > 0 && (
            <div className="upload-stats" style={{ marginTop: '8px', fontSize: '12px', color: '#888' }}>
              {uploadStats.filesProcessed && <span>已处理: {uploadStats.filesProcessed} 个文件</span>}
              {uploadStats.totalFiles && <span> / 总计: {uploadStats.totalFiles} 个文件</span>}
              {uploadStats.bytesProcessed && <span> / 大小: {(uploadStats.bytesProcessed / 1024 / 1024).toFixed(2)} MB</span>}
            </div>
          )}
        </div>
      )}
      
      {!isUploading && uploadResult && (
        <div className="result-container">
          <div className={`result-card ${uploadResult?.success ? 'success' : 'error'}`}>
            <div className="result-header">
              {uploadResult?.success ? (
                <span className="success-icon">✅ 上传成功！</span>
              ) : (
                <span className="error-icon">❌ 上传失败</span>
              )}
            </div>
            
            {uploadResult?.success ? (
              /* Success state */
              <div className="result-details">
                <div className="success-summary" style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '150px 1fr', gap: '8px', marginBottom: '16px' }}>
                    <span style={{ fontWeight: 'bold' }}>仓库:</span>
                    <span>{uploadResult.repo}</span>
                    
                    <span style={{ fontWeight: 'bold' }}>分支:</span>
                    <span>{uploadResult.branch}</span>
                    
                    <span style={{ fontWeight: 'bold' }}>文件数:</span>
                    <span>{uploadResult.statistics?.file_count || 0}</span>
                    
                    <span style={{ fontWeight: 'bold' }}>大小:</span>
                    <span>{uploadResult.statistics?.total_size_mb || '0'} MB</span>
                    
                    <span style={{ fontWeight: 'bold' }}>耗时:</span>
                    <span>{uploadResult.took} ms</span>
                    
                    {uploadResult.commit_sha && (
                      <>
                        <span style={{ fontWeight: 'bold' }}>本地提交 SHA:</span>
                        <span>{uploadResult.commit_sha}</span>
                      </>
                    )}
                    
                    {uploadResult.remote_sha && (
                      <>
                        <span style={{ fontWeight: 'bold' }}>远程分支 SHA:</span>
                        <span>{uploadResult.remote_sha}</span>
                      </>
                    )}
                  </div>
                  
                  {/* Success message */}
                  <div className="success-message" style={{ color: '#28a745', marginBottom: '16px' }}>
                    {uploadResult.statistics?.file_count > 0 ? '上传成功完成' : '没有需要上传的更改（文件已是最新）'}
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
                    🔗 在 GitHub 上查看
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
                    再次上传
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
                        <h4 style={{ margin: 0, fontSize: '14px', color: '#666' }}>错误详情:</h4>
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
                      <h4 style={{ margin: 0, fontSize: '14px', color: '#666', marginBottom: '8px' }}>推送输出:</h4>
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
                    耗时: {uploadResult.took} ms
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
              重新开始
            </button>
          </div>
        </div>
      )}
      
      {!isUploading && !uploadResult && (
        <div className="empty-state">
          <p>上传尚未开始。</p>
        </div>
      )}
    </div>
  );
};

export default StepUpload;

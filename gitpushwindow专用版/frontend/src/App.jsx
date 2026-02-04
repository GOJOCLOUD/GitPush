import React, { useState, useRef } from 'react';
import { runPythonUpload } from './services/api.js';

// Step components
import StepToken from './components/steps/StepToken';
import StepRepo from './components/steps/StepRepo';
import StepBranch from './components/steps/StepBranch';
import StepFile from './components/steps/StepFile';
import StepUpload from './components/steps/StepUpload';

function App() {
  // Core state
  const [step, setStep] = useState(1);
  const [token, setToken] = useState('');
  const [repo, setRepo] = useState('');
  const [branch, setBranch] = useState('');
  const [path, setPath] = useState('');
  const [proxy, setProxy] = useState('');
  const [uploadResult, setUploadResult] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStage, setUploadStage] = useState('');
  const [uploadStats, setUploadStats] = useState({});
  const [conflictStrategy, setConflictStrategy] = useState('overwrite');
  const [ignorePatterns, setIgnorePatterns] = useState('.git\nnode_modules\ndist\nbuild\n.DS_Store\n*.log\n*.tmp');
  const [cancelUpload, setCancelUpload] = useState(false);
  
  // Upload controller ref for cancellation
  const uploadControllerRef = useRef(null);

  // Step navigation handlers
  const handleNext = () => {
    setStep(step + 1);
  };

  const handlePrevious = () => {
    setStep(step - 1);
  };

  const handleReset = () => {
    setStep(1);
    setToken('');
    setRepo('');
    setBranch('');
    setPath('');
    setProxy('');
    setUploadResult(null);
    setIsUploading(false);
    setUploadStage('');
    setUploadStats({});
    setConflictStrategy('overwrite');
    setIgnorePatterns('.git\nnode_modules\ndist\nbuild\n.DS_Store\n*.log\n*.tmp');
    setCancelUpload(false);
    uploadControllerRef.current = null;
  };

  // Retry upload with current params
  const handleRetry = () => {
    setUploadResult(null);
    handleUpload();
  };

  // Cancel upload
  const handleCancelUpload = () => {
    setCancelUpload(true);
    setUploadStage('cancelling');
    // Here you would typically send a cancellation signal to the backend
    // For now, we'll just simulate cancellation
    setTimeout(() => {
      setIsUploading(false);
      setUploadStage('');
      setUploadResult({
        success: false,
        message: '上传已取消',
        took: 0
      });
    }, 500);
  };

  // Upload handler
  const handleUpload = async () => {
    setIsUploading(true);
    setUploadResult(null);
    setUploadStage('uploading');
    setCancelUpload(false);
    
    try {
      // Print the path before sending to backend
      console.log("UPLOAD_DEBUG_PATH =", path);
      // Upload start log
      console.info("UPLOAD start", {repo, branch, path, proxy, conflictStrategy});
      
      // Update upload stats with initial values
      setUploadStats({
        filesProcessed: 0,
        totalFiles: Array.isArray(path) ? path.length : 1,
        bytesProcessed: 0
      });

      // 处理 ignore patterns（按行拆分，过滤空行）
      const patternsArray = (ignorePatterns || '')
        .split(/\r?\n|,/)
        .map(p => p.trim())
        .filter(Boolean);
      
      const result = await runPythonUpload(token, repo, branch, path, proxy, conflictStrategy, patternsArray);
      
      // Upload success log
      console.info("UPLOAD result", result);
      
      // Ensure uploadResult contains all required fields
      const stats = result.statistics || {};
      const structuredResult = {
        ...result,
        repo,
        branch,
        stats: {
          count: stats.file_count,
          size: stats.total_size_bytes,
          sizeFormatted: stats.total_size_mb ? stats.total_size_mb + ' MB' : '0 MB'
        },
        took: result.took || 0
      };
      
      // Set final stage
      setUploadStage('done');
      
      // Ensure uploadResult is updated first before switching step
      setUploadResult(structuredResult);
      // Set step after uploadResult is updated
      setTimeout(() => setStep(5), 0); // Go to results step with next tick
    } catch (error) {
      // Upload failure log
      console.error("UPLOAD failed", error);
      
      // Ensure uploadResult is structured correctly for the UI
      const structuredError = {
        success: false,
        message: error.message || '上传失败',
        stderr: error.stderr || error.message,
        took: error.took || 0
      };
      
      setUploadResult(structuredError);
      // Set step after uploadResult is updated
      setTimeout(() => setStep(5), 0); // Go to results step with next tick
    } finally {
      setIsUploading(false);
      setCancelUpload(false);
      uploadControllerRef.current = null;
    }
  };

  // Render current step
  const renderStep = () => {
    switch (step) {
      case 1:
        return (
          <StepToken 
            token={token} 
            setToken={setToken} 
            proxy={proxy}
            setProxy={setProxy}
            onNext={handleNext} 
          />
        );
      case 2:
        return (
          <StepRepo 
            token={token} 
            onRepoSelect={setRepo} 
            onNext={handleNext} 
            selectedRepo={repo}
            proxy={proxy}
          />
        );
      case 3:
        return (
          <StepBranch 
            repo={repo} 
            onBranchSelect={setBranch} 
            onNext={handleNext} 
            selectedBranch={branch}
            token={token}
            proxy={proxy}
          />
        );
      case 4:
        return (
          <StepFile 
            onPathSelect={setPath} 
            onUpload={handleUpload} 
            selectedPath={path}
            onConflictStrategyChange={setConflictStrategy}
            conflictStrategy={conflictStrategy}
            ignorePatterns={ignorePatterns}
            onIgnorePatternsChange={setIgnorePatterns}
          />
        );
      case 5:
        return (
          <StepUpload 
            uploadResult={uploadResult} 
            isUploading={isUploading} 
            onReset={handleReset}
            onRetry={handleRetry}
            uploadStage={uploadStage}
            uploadStats={uploadStats}
          />
        );
      default:
        return <StepToken token={token} setToken={setToken} onNext={handleNext} />;
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <div className="app-header">
        <h1 className="app-title">📤 GitPush</h1>
        <p className="app-subtitle">便捷的 GitHub 文件上传工具</p>
      </div>
      
      {/* Step indicator */}
      <div className="step-indicator">
        <div className="step-buttons">
          {[1, 2, 3, 4, 5].map((stepNum) => (
            <button 
              key={stepNum} 
              className={`step-button ${stepNum === step ? 'active' : ''} ${stepNum < step ? 'completed' : ''}`}
              disabled={stepNum > step + 1}
              onClick={() => setStep(stepNum)}
            >
              {stepNum}
            </button>
          ))}
        </div>
        <div className="step-labels">
          <span className={step === 1 ? 'active' : ''}>令牌</span>
          <span className={step === 2 ? 'active' : ''}>仓库</span>
          <span className={step === 3 ? 'active' : ''}>分支</span>
          <span className={step === 4 ? 'active' : ''}>文件</span>
          <span className={step === 5 ? 'active' : ''}>结果</span>
        </div>
      </div>
      
      {/* Main content */}
      <div className="main-content">
        <div className="step-container">
          {renderStep()}
        </div>
      </div>
      
      {/* Footer */}
      <div className="app-footer">
        <p className="footer-text">
          便捷的 GitHub 文件上传工具
        </p>
        <p className="footer-text" style={{ fontSize: '0.9em', color: '#666', marginTop: '8px' }}>
          📝 本工具仅与 GitHub 交互，不会向第三方上传数据；令牌存储在本地，可随时删除
        </p>
      </div>
      
      {/* Upload Overlay */}
      {isUploading && (
        <div className="upload-overlay">
          <div className="upload-loading-container">
            <div className="upload-spinner"></div>
            <div className="upload-loading-text">正在上传...</div>
            <div className="upload-loading-subtext">请稍候，正在处理文件</div>
            <div className="upload-loading-stage">
              {uploadStage === 'uploading' ? '📤 正在上传文件到 GitHub' : 
               uploadStage === 'cancelling' ? '❌ 正在取消...' : 
               '⏳ 准备中...'}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;

import React, { useEffect, useState, useCallback } from 'react';
import { getBranches } from '../../services/api.js';

const StepBranch = ({ repo, onBranchSelect, onNext, selectedBranch, token, proxy = '' }) => {
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [newBranch, setNewBranch] = useState('');
  const [useNewBranch, setUseNewBranch] = useState(false);
  const [fetchStats, setFetchStats] = useState({ took: 0, retries: 0 });
  const [branchError, setBranchError] = useState('');
  const [isBranchValid, setIsBranchValid] = useState(true);

  // Validate branch name
  const validateBranchName = (name) => {
    if (!name.trim()) {
      setIsBranchValid(true);
      setBranchError('');
      return true;
    }
    
    const isValid = /^[a-zA-Z0-9-_/]+$/.test(name);
    setIsBranchValid(isValid);
    setBranchError(isValid ? '' : 'Branch name can only contain letters, numbers, -_/');
    return isValid;
  };

  // Fetch branches when repo changes
  useEffect(() => {
    fetchBranches();
  }, [repo, token, proxy]);

  const fetchBranches = useCallback(async () => {
    if (!repo || !token) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await getBranches(token, repo, proxy);
      
      if (result.success) {
        const fetchedBranches = result.branches || [];
        setBranches(fetchedBranches);
        setFetchStats(prev => ({
          took: result.took || 0,
          retries: prev.retries + 1
        }));
        
        // Empty list fallback: if no branches, don't auto-select but prompt for default branch
        if (!selectedBranch) {
          if (fetchedBranches.includes('main')) {
            onBranchSelect('main');
          } else if (fetchedBranches.includes('master')) {
            onBranchSelect('master');
          } else {
            // No branches, clear selection and let user input
            onBranchSelect('');
          }
        }
      } else {
        setError({
          message: result.message || 'Failed to fetch branch list',
          statusCode: result.statusCode,
          stderr: result.stderr
        });
        // Also set default branch prompt on failure
        if (!selectedBranch) {
          // Set to empty, let user input
          onBranchSelect('');
        }
      }
    } catch (err) {
      setError({
        message: 'Failed to fetch branch list, please check network connection',
        stderr: err.message
      });
      console.error('Error fetching branches:', err);
      // Also set default branch prompt on failure
      if (!selectedBranch) {
        onBranchSelect('');
      }
    } finally {
      setLoading(false);
    }
  }, [repo, token, proxy, selectedBranch, onBranchSelect]);

  const handleBranchChange = (e) => {
    setUseNewBranch(false);
    setNewBranch('');
    setIsBranchValid(true);
    setBranchError('');
    onBranchSelect(e.target.value);
  };

  const handleNewBranchChange = (e) => {
    const value = e.target.value;
    setNewBranch(value);
    setUseNewBranch(true);
    validateBranchName(value);
    onBranchSelect(value);
  };

  const handleNext = () => {
    const branch = selectedBranch || newBranch;
    const trimmedBranch = branch.trim();
    
    if (!trimmedBranch) {
      setError({
        message: 'Please select or create a branch',
        isValidationError: true
      });
      return;
    }
    
    if (!isBranchValid) {
      setError({
        message: branchError,
        isValidationError: true
      });
      return;
    }
    
    // Trim whitespace
    onBranchSelect(trimmedBranch);
    
    // No longer create branch in advance, go to next step directly
    // Branch creation will be handled automatically by backend during upload
    onNext();
  };

  return (
    <div className="step-content">
      <h3 className="step-title">步骤 3：选择或创建分支</h3>
      <p className="step-description">
        选择现有分支或创建新分支用于上传。
      </p>
      
      {loading && (
        <div className="loading-indicator">
          <span>正在加载分支...</span>
        </div>
      )}
      
      {error && (
        <div className="error-message">
          ❌ {error.message}
          {error.statusCode && <span className="status-code"> (状态码: {error.statusCode})</span>}
          {error.stderr && (
            <div className="error-details" style={{ marginTop: '8px', fontSize: '12px', color: '#ff6b6b' }}>
              {error.stderr.slice(0, 200)}...
            </div>
          )}
          {!error.isValidationError && (
            <div style={{ marginTop: '8px' }}>
              <button type="button" className="btn-secondary" onClick={fetchBranches} disabled={loading}>
                重试
              </button>
            </div>
          )}
        </div>
      )}
      
      {!loading && (
        <div className="fetch-stats" style={{ fontSize: '12px', color: '#666', marginBottom: '16px' }}>
          {branches.length > 0 ? (
            <span>共 {branches.length} 个分支，耗时 {fetchStats.took}ms</span>
          ) : error ? (
            <span style={{ color: '#ff6b6b' }}>获取分支失败。请重试或创建新分支。</span>
          ) : (
            <span>此仓库中没有分支。请在下方创建新分支。</span>
          )}
          {fetchStats.retries > 1 && <span> (重试 {fetchStats.retries - 1} 次)</span>}
        </div>
      )}
      
      {!loading && (
        <div className="action-card">
          {branches.length > 0 && (
            <div className="form-group">
              <label className="form-label" htmlFor="branch-select">
                选择现有分支
              </label>
              <select
                id="branch-select"
                className="form-control"
                value={!useNewBranch ? selectedBranch : ''}
                onChange={handleBranchChange}
                disabled={newBranch.trim() !== ''}
                style={{ opacity: newBranch.trim() !== '' ? 0.6 : 1 }}
              >
                <option value="">-- 选择分支 --</option>
                {branches.map((branch) => (
                  <option key={branch} value={branch}>
                    {branch}
                  </option>
                ))}
              </select>
            </div>
          )}
          
          <div className="form-group" style={{ marginTop: branches.length > 0 ? '20px' : '0' }}>
            <label className="form-label" htmlFor="new-branch-input">
              {branches.length > 0 ? '或创建新分支' : '创建新分支'}
            </label>
            <input
              id="new-branch-input"
              type="text"
              className="form-control"
              placeholder={branches.length === 0 ? 'main' : 'new-feature'}
              value={newBranch}
              onChange={handleNewBranchChange}
              style={{
                borderColor: branchError ? '#ff6b6b' : '',
                outlineColor: branchError ? '#ff6b6b' : ''
              }}
            />
            {branchError && (
              <p className="error-text" style={{ color: '#ff6b6b', fontSize: '12px', marginTop: '4px' }}>
                {branchError}
              </p>
            )}
            <p className="form-hint" style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
              分支名称只能包含字母、数字、-_/
            </p>
          </div>
        </div>
      )}
      
      <div className="step-navigation">
        <button 
          type="button" 
          className="btn-primary" 
          onClick={handleNext}
          disabled={!selectedBranch && !newBranch.trim()}
        >
          下一步 →
        </button>
      </div>
    </div>
  );
};

export default StepBranch;

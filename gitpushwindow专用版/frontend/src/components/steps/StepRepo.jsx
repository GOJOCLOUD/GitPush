import React, { useEffect, useState, useCallback } from 'react';
import { getRepos } from '../../services/api.js';

const StepRepo = ({ token, onRepoSelect, onNext, selectedRepo, proxy = '' }) => {
  const [repos, setRepos] = useState([]);
  const [filteredRepos, setFilteredRepos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [manualRepo, setManualRepo] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [fetchStats, setFetchStats] = useState({ count: 0, took: 0, retries: 0 });

  const fetchRepos = useCallback(async () => {
    if (!token) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await getRepos(token, proxy);
      
      if (result.success) {
        const reposList = result.repos || [];
        setRepos(reposList);
        setFilteredRepos(reposList);
        setFetchStats((prev) => ({
          count: reposList.length,
          took: result.took || 0,
          retries: prev.retries + 1
        }));
      } else {
        setError({
          message: result.message || '获取仓库列表失败',
          statusCode: result.statusCode,
          stderr: result.stderr
        });
      }
    } catch (err) {
      setError({
        message: '获取仓库列表失败，请检查网络连接和令牌',
        stderr: err.message
      });
      console.error('Error fetching repos:', err);
    } finally {
      setLoading(false);
    }
  }, [token, proxy]);

  // Filter repos based on search term
  useEffect(() => {
    if (!searchTerm.trim()) {
      setFilteredRepos(repos);
    } else {
      const term = searchTerm.toLowerCase();
      setFilteredRepos(repos.filter(repo => 
        repo.full_name.toLowerCase().includes(term) ||
        (repo.description && repo.description.toLowerCase().includes(term))
      ));
    }
  }, [repos, searchTerm]);

  // Fetch repos when token changes
  useEffect(() => {
    fetchRepos();
  }, [token, fetchRepos]);

  const handleRepoClick = (repo) => {
    onRepoSelect(repo.full_name);
    setManualRepo('');
  };

  const handleNext = () => {
    const candidate = selectedRepo || manualRepo;
    if (!candidate || !candidate.trim()) {
      setError({
        message: 'Please select or enter a repository first',
        isValidationError: true
      });
      return;
    }
    onRepoSelect(candidate.trim());
    onNext();
  };

  return (
    <div className="step-content">
      <h3 className="step-title">步骤 2: 选择仓库</h3>
      <p className="step-description">
        选择您要上传到的仓库。
      </p>
      
      {loading && (
        <div className="loading-indicator">
          <span>正在加载仓库...</span>
        </div>
      )}
      
      {error && (
        <div className="error-message">
          ❌ {error.message}
          {error.statusCode && <span className="status-code"> (Status: {error.statusCode})</span>}
          {error.stderr && (
            <div className="error-details" style={{ marginTop: '8px', fontSize: '12px', color: '#ff6b6b' }}>
              {error.stderr.slice(0, 200)}...
            </div>
          )}
          {!error.isValidationError && (
            <div style={{ marginTop: '8px' }}>
              <button type="button" className="btn-secondary" onClick={fetchRepos} disabled={loading}>
                Retry
              </button>
            </div>
          )}
          {error.statusCode === 401 && <p className="error-suggestion">Suggestion: Check if token permissions are correct</p>}
          {error.statusCode === 403 && <p className="error-suggestion">Suggestion: GitHub API rate limit may have been triggered</p>}
        </div>
      )}
      
      {!loading && !error && (
        <div className="fetch-stats">
          <span>共 {fetchStats.count} 个仓库，耗时 {fetchStats.took}ms</span>
          {fetchStats.retries > 1 && <span> (重试 {fetchStats.retries - 1} 次)</span>}
        </div>
      )}
      
      {!loading && repos.length > 0 && (
        <div className="search-container" style={{ marginBottom: '16px' }}>
          <input
            type="text"
            className="form-control"
            placeholder="搜索仓库..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      )}
      
      {!loading && !error && filteredRepos.length === 0 && repos.length > 0 && (
        <div className="empty-state">
          <p>未找到匹配的仓库，请调整搜索条件。</p>
        </div>
      )}
      
      {!loading && !error && filteredRepos.length === 0 && repos.length === 0 && (
        <div className="empty-state">
          <p>未找到仓库，请检查令牌权限或直接输入仓库名称。</p>
        </div>
      )}
      
      {!loading && !error && filteredRepos.length > 0 && (
        <div className="repo-grid">
          {filteredRepos.map((repo) => (
            <div 
              key={repo.full_name} 
              className={`repo-card ${selectedRepo === repo.full_name ? 'selected' : ''}`}
              onClick={() => handleRepoClick(repo)}
            >
              <div className="repo-header">
                <strong>{repo.full_name}</strong>
              </div>
              <div className="repo-description">
                {repo.description || '无描述'}
              </div>
            </div>
          ))}
        </div>
      )}
      
      <div className="action-card" style={{ marginTop: '16px' }}>
        <div className="form-group">
          <label className="form-label" htmlFor="manual-repo">
            或手动输入仓库（所有者/仓库）
          </label>
          <input
            id="manual-repo"
            type="text"
            className="form-control"
            placeholder="owner/repo"
            value={manualRepo}
            onChange={(e) => {
              setManualRepo(e.target.value);
              onRepoSelect('');
            }}
          />
          <p className="form-hint">当列表加载失败或仓库不存在时可直接输入。</p>
        </div>
      </div>
      
      <div className="step-navigation">
        <button 
          type="button" 
          className="btn-primary" 
          onClick={handleNext}
          disabled={!selectedRepo && !manualRepo.trim()}
        >
          下一步 →
        </button>
      </div>
    </div>
  );
};

export default StepRepo;

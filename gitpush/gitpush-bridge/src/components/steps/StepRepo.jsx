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
          message: result.message || 'Failed to fetch repository list',
          statusCode: result.statusCode,
          stderr: result.stderr
        });
      }
    } catch (err) {
      setError({
        message: 'Failed to fetch repository list, please check network connection and token',
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
      <h3 className="step-title">Step 2: Select Repository</h3>
      <p className="step-description">
        Choose which repository you want to upload to.
      </p>
      
      {loading && (
        <div className="loading-indicator">
          <span>Loading repositories...</span>
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
          <span>Total {fetchStats.count} repositories, took {fetchStats.took}ms</span>
          {fetchStats.retries > 1 && <span> (retried {fetchStats.retries - 1} times)</span>}
        </div>
      )}
      
      {!loading && repos.length > 0 && (
        <div className="search-container" style={{ marginBottom: '16px' }}>
          <input
            type="text"
            className="form-control"
            placeholder="Search repositories..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      )}
      
      {!loading && !error && filteredRepos.length === 0 && repos.length > 0 && (
        <div className="empty-state">
          <p>No matching repositories found, please adjust your search criteria.</p>
        </div>
      )}
      
      {!loading && !error && filteredRepos.length === 0 && repos.length === 0 && (
        <div className="empty-state">
          <p>No repositories found, please check token permissions or enter repository name directly.</p>
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
                {repo.description || 'No description'}
              </div>
            </div>
          ))}
        </div>
      )}
      
      <div className="action-card" style={{ marginTop: '16px' }}>
        <div className="form-group">
          <label className="form-label" htmlFor="manual-repo">
            Or enter repository manually (owner/repo)
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
          <p className="form-hint">Enter directly when list loading fails or repository is missing.</p>
        </div>
      </div>
      
      <div className="step-navigation">
        <button 
          type="button" 
          className="btn-primary" 
          onClick={handleNext}
          disabled={!selectedRepo && !manualRepo.trim()}
        >
          Next →
        </button>
      </div>
    </div>
  );
};

export default StepRepo;

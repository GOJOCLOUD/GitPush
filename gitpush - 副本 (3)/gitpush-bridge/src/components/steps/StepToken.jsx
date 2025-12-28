import React, { useState } from 'react';
import { saveToken, validateToken } from '../../services/api.js';
import TokenManager from '../TokenManager';

const StepToken = ({ token, setToken, onNext, proxy, setProxy }) => {
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showTokenManager, setShowTokenManager] = useState(false);

  const openGitHubTokenPage = () => {
    try {
      // Use a safer approach that works in both web and Tauri environments
      const a = document.createElement('a');
      a.href = 'https://github.com/settings/tokens';
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error opening GitHub token page:', error);
      setError('Failed to open GitHub token page. Please open it manually.');
    }
  };

  const handleSaveToken = async () => {
    if (!token.trim()) {
      setError('Token cannot be empty');
      return;
    }

    setIsSaving(true);
    setError('');
    setSuccess('');

    try {
        // Validate token using backend, passing proxy parameter
        const validationResult = await validateToken(token, proxy);
        if (!validationResult.success) {
          throw new Error(validationResult.message);
        }
        
        const saveResult = await saveToken(token, proxy);
        if (!saveResult.success) {
          throw new Error(saveResult.message);
        }
        
        setSuccess('Token verified and saved successfully');
        onNext();
      } catch (err) {
        setError(err.message || 'Failed to save token. Please try again.');
        console.error('Error saving token:', err);
      } finally {
        setIsSaving(false);
      }
  };

  return (
    <div className="step-content">
      <h3 className="step-title">Step 1: Get GitHub Token</h3>
      <p className="step-description">
        To upload to GitHub, you need a Personal Access Token with repo permissions.
      </p>
      
      <div className="action-card">
        <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
          <button 
            type="button" 
            className="btn-secondary" 
            onClick={openGitHubTokenPage}
            style={{ flex: 1 }}
          >
            🔗 Get GitHub Token
          </button>
          <button 
            type="button" 
            className="btn-secondary" 
            onClick={() => setShowTokenManager(true)}
            style={{ flex: 1 }}
          >
            📋 管理 Token
          </button>
        </div>
        
        <div className="form-group">
          <label className="form-label" htmlFor="token-input">
            Personal Access Token
          </label>
          <input
            id="token-input"
            type="password"
            className="form-control"
            placeholder="ghp_xxxxxxxxxxxx"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            autoFocus
          />
          <p className="form-hint">
            After generating your token, paste it here and click Save Token.
          </p>
          <p className="form-hint" style={{ color: '#666', fontSize: '0.9em' }}>
            💡 Token is saved in plain text at ~/.gitpush_token, can be deleted/replaced anytime; repo permission is recommended
          </p>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="proxy-input">
            Proxy (optional)
          </label>
          <input
            id="proxy-input"
            type="text"
            className="form-control"
            placeholder="http://127.0.0.1:7890"
            value={proxy}
            onChange={(e) => setProxy(e.target.value)}
          />
          <p className="form-hint">
            Connect directly to GitHub if no proxy is filled (faster); forward through backend if proxy is filled (supports blocked environments)
          </p>
        </div>

        {error && (
          <div className="error-message" style={{ color: 'red', marginTop: '8px' }}>
            {error}
          </div>
        )}
        {success && (
          <div className="result-card success" style={{ marginTop: '8px' }}>
            {success}
          </div>
        )}
      </div>
      
      <div className="step-navigation">
        <button 
          type="button" 
          className="btn-primary" 
          onClick={handleSaveToken}
          disabled={!token.trim() || isSaving}
        >
          {isSaving ? 'Saving...' : 'Save Token →'}
        </button>
      </div>

      <TokenManager 
        isOpen={showTokenManager}
        onClose={() => setShowTokenManager(false)}
        onSelectToken={(selectedToken) => setToken(selectedToken)}
      />
    </div>
  );
};

export default StepToken;

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
      const a = document.createElement('a');
      a.href = 'https://github.com/settings/tokens';
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error opening GitHub token page:', error);
      setError('打开 GitHub 令牌页面失败，请手动打开。');
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
      <h3 className="step-title">步骤 1: 获取 GitHub 令牌</h3>
      <p className="step-description">
        要上传到 GitHub，您需要一个具有 repo 权限的个人访问令牌。
      </p>
      
      <div className="action-card">
        <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
          <button 
            type="button" 
            className="btn-secondary" 
            onClick={openGitHubTokenPage}
            style={{ flex: 1 }}
          >
            🔗 获取 GitHub 令牌
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
            个人访问令牌
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
            生成令牌后，将其粘贴到此处并点击"保存令牌"。
          </p>
          <p className="form-hint" style={{ color: '#666', fontSize: '0.9em' }}>
            💡 Token 以明文形式保存在 ~/.gitpush_token，可随时删除/替换；建议使用 repo 权限
          </p>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="proxy-input">
            代理（可选）
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
            不填写代理则直接连接 GitHub（更快）；填写代理则通过后端转发（支持被屏蔽的环境）
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
          {isSaving ? '保存中...' : '保存令牌 →'}
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

import React, { useState, useEffect } from 'react';

const TokenManager = ({ isOpen, onClose, onSelectToken }) => {
  const [tokens, setTokens] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newToken, setNewToken] = useState('');
  const [newNote, setNewNote] = useState('');

  useEffect(() => {
    if (isOpen) {
      loadTokens();
    }
  }, [isOpen]);

  const loadTokens = () => {
    try {
      const saved = localStorage.getItem('gitpush_tokens');
      if (saved) {
        setTokens(JSON.parse(saved));
      }
    } catch (error) {
      console.error('Error loading tokens:', error);
    }
  };

  const saveTokens = (updatedTokens) => {
    try {
      localStorage.setItem('gitpush_tokens', JSON.stringify(updatedTokens));
      setTokens(updatedTokens);
    } catch (error) {
      console.error('Error saving tokens:', error);
    }
  };

  const handleAddToken = () => {
    if (!newToken.trim()) {
      alert('Token cannot be empty');
      return;
    }

    const tokenEntry = {
      id: Date.now(),
      token: newToken.trim(),
      note: newNote.trim() || `Token ${tokens.length + 1}`,
      createdAt: new Date().toISOString()
    };

    const updatedTokens = [...tokens, tokenEntry];
    saveTokens(updatedTokens);

    setNewToken('');
    setNewNote('');
    setShowAddForm(false);
  };

  const handleDeleteToken = (id) => {
    if (window.confirm('Are you sure you want to delete this token?')) {
      const updatedTokens = tokens.filter(t => t.id !== id);
      saveTokens(updatedTokens);
    }
  };

  const handleUpdateNote = (id, newNote) => {
    const updatedTokens = tokens.map(t => 
      t.id === id ? { ...t, note: newNote } : t
    );
    saveTokens(updatedTokens);
  };

  const handleSelectToken = (token) => {
    onSelectToken(token);
    onClose();
  };

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const maskToken = (token) => {
    if (token.length <= 10) return token;
    return token.substring(0, 6) + '...' + token.substring(token.length - 4);
  };

  if (!isOpen) return null;

  return (
    <div className="token-manager-overlay">
      <div className="token-manager-container">
        <div className="token-manager-header">
          <h2 className="token-manager-title">Token Manager</h2>
          <button 
            className="token-manager-close"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <div className="token-manager-content">
          <div className="token-manager-actions">
            <button 
              className="btn-primary"
              onClick={() => setShowAddForm(true)}
            >
              Add Token
            </button>
          </div>

          {showAddForm && (
            <div className="token-add-form">
              <div className="form-group">
                <label className="form-label">Token</label>
                <input
                  type="password"
                  className="form-control"
                  placeholder="ghp_xxxxxxxxxxxx"
                  value={newToken}
                  onChange={(e) => setNewToken(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Note</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g., Personal Account Token"
                  value={newNote}
                  onChange={(e) => setNewNote(e.target.value)}
                />
              </div>
              <div className="token-form-actions">
                <button 
                  className="btn-primary"
                  onClick={handleAddToken}
                  disabled={!newToken.trim()}
                >
                  Save
                </button>
                <button 
                  className="btn-secondary"
                  onClick={() => {
                    setShowAddForm(false);
                    setNewToken('');
                    setNewNote('');
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          <div className="token-list">
            {tokens.length === 0 ? (
              <div className="token-empty">
                <p>No saved tokens</p>
                <p className="token-empty-hint">Click "Add Token" button to save your token</p>
              </div>
            ) : (
              tokens.map((tokenEntry) => (
                <div key={tokenEntry.id} className="token-item">
                  <div className="token-item-header">
                    <input
                      type="text"
                      className="token-note-input"
                      value={tokenEntry.note}
                      onChange={(e) => handleUpdateNote(tokenEntry.id, e.target.value)}
                    />
                    <div className="token-item-actions">
                      <button 
                        className="token-use-btn"
                        onClick={() => handleSelectToken(tokenEntry.token)}
                        title="Use this token"
                      >
                        Use
                      </button>
                      <button 
                        className="token-delete-btn"
                        onClick={() => handleDeleteToken(tokenEntry.id)}
                        title="Delete"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <div className="token-item-details">
                    <span className="token-value">{maskToken(tokenEntry.token)}</span>
                    <span className="token-date">{formatDate(tokenEntry.createdAt)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TokenManager;

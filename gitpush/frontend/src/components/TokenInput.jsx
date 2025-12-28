import React from 'react';

const TokenInput = ({ value, onChange }) => {
  return (
    <div className="form-group">
      <label className="form-label" htmlFor="token-input">
        Personal Access Token
      </label>
      <input
        id="token-input"
        type="password"
        className="form-control"
        placeholder="ghp_xxxxxxxxxxxx"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
};

export default TokenInput;
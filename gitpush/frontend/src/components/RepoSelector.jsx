import React from 'react';

const RepoSelector = ({ value, onChange }) => {
  return (
    <div className="form-group">
      <label className="form-label" htmlFor="repo-input">
        仓库（owner/repo）
      </label>
      <input
        id="repo-input"
        type="text"
        className="form-control"
        placeholder="octocat/Hello-World"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
};

export default RepoSelector;
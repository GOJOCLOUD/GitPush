import React from 'react';

const BranchSelector = ({ value, onChange }) => {
  return (
    <div className="form-group">
      <label className="form-label" htmlFor="branch-input">
        分支名称
      </label>
      <input
        id="branch-input"
        type="text"
        className="form-control"
        placeholder="main"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
};

export default BranchSelector;
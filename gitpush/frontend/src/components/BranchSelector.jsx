import React from 'react';

const BranchSelector = ({ value, onChange }) => {
  return (
    <div className="form-group">
      <label className="form-label" htmlFor="branch-input">
        Branch Name
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
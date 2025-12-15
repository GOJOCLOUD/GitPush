import React from 'react';

const PathSelector = ({ value, onChange }) => {
  return (
    <div className="form-group">
      <label className="form-label" htmlFor="path-input">
        Local Path (File or Directory)
      </label>
      <input
        id="path-input"
        type="text"
        className="form-control"
        placeholder="/Users/name/projects/my-file.txt"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
};

export default PathSelector;
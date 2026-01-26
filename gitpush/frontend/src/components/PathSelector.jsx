import React from 'react';

const PathSelector = ({ value, onChange }) => {
  return (
    <div className="form-group">
      <label className="form-label" htmlFor="path-input">
        本地路径（文件或目录）
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
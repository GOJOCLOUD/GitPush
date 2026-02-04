import React from 'react';

const UploadButton = ({ onClick, isLoading }) => {
  return (
    <div className="form-group" style={{ marginTop: '24px' }}>
      <button
        type="button"
        className="btn-primary"
        onClick={onClick}
        disabled={isLoading}
      >
        {isLoading ? '正在上传到 GitHub...' : '上传到仓库'}
      </button>
    </div>
  );
};

export default UploadButton;
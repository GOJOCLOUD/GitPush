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
        {isLoading ? 'Uploading to GitHub...' : 'Upload to Repository'}
      </button>
    </div>
  );
};

export default UploadButton;
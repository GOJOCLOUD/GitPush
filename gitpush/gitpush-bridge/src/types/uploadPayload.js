/**
 * Upload payload structure for run_python_upload command
 * @typedef {Object} UploadPayload
 * @property {string} token - GitHub Personal Access Token
 * @property {string} repo - Repository in format "owner/repo"
 * @property {string} branch - Git branch name
 * @property {string} path - Local file or directory path
 */

/**
 * Create upload payload object
 * @param {string} token - GitHub Token
 * @param {string} repo - Repository name
 * @param {string} branch - Branch name
 * @param {string} path - Local path
 * @returns {UploadPayload} Upload payload object
 */
export function createUploadPayload(token, repo, branch, path) {
  return {
    token,
    repo,
    branch,
    path
  };
}

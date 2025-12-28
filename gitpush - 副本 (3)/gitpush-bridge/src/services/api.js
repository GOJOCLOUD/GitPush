import { invoke } from '@tauri-apps/api/core';
import { resolve } from '@tauri-apps/api/path';
import apiClient from './apiClient';
// fs operations are now handled by the backend due to Tauri 2.x changes

// Mock writeTextFile function for now - will be replaced with backend call
async function writeTextFile(filename, content, options) {
  // In Tauri 2.x, we need to use invoke to call backend for file operations
  return await invoke('write_text_file', {
    filename,
    content,
    options
  });
}

// Mock BaseDirectory enum
const BaseDirectory = {
  Home: 'home'
};

/**
 * Mask token for safe logging
 */
function maskToken(token) {
  if (!token) return '';
  return token.length > 8 ? `${token.slice(0, 4)}***${token.slice(-4)}` : '***';
}

/**
 * Check if we should use backend based on proxy
 */
function shouldUseBackend(proxy) {
  return !!proxy && proxy.trim() !== '';
}

/**
 * Fetch with timeout wrapper
 */
async function fetchWithTimeout(url, { headers, timeout = 8000, ...options } = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal
    });
    return response;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(`Request timeout (${timeout}ms)`);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Validate GitHub token
 */
export async function validateToken(token, proxy = '') {
  const trimmed = token.trim();
  if (!trimmed) {
    return { success: false, message: 'Token cannot be empty' };
  }
  
  const startTime = performance.now();
  
  try {
    const response = await apiClient.post('/git/validate/token', {
      token: trimmed
    });
    
    const endTime = performance.now();
    
    if (response.code === 0 && response.data) {
      return {
        success: true,
        message: response.message,
        user: response.data.user,
        took: Math.round(endTime - startTime)
      };
    }
    
    return {
      success: false,
      message: response.message || 'Token validation failed',
      took: Math.round(endTime - startTime)
    };
  } catch (error) {
    const endTime = performance.now();
    console.error('validateToken error:', error);
    
    return {
      success: false,
      message: error.response?.data?.message || error.message || 'Token validation failed',
      stderr: error.response?.data?.detail || error.message,
      took: Math.round(endTime - startTime)
    };
  }
}

/**
 * Get repositories from GitHub
 */
export async function getRepos(token, proxy = '') {
  const trimmedToken = token.trim();
  if (!trimmedToken) {
    return { success: false, message: 'Token cannot be empty' };
  }
  
  const startTime = performance.now();
  
  try {
    const response = await apiClient.post('/git/get/repos', {
      token: trimmedToken
    });
    
    const endTime = performance.now();
    
    if (response.code === 0 && response.data) {
      return {
        success: true,
        repos: response.data.repos,
        took: Math.round(endTime - startTime)
      };
    }
    
    return {
      success: false,
      message: response.message || 'Failed to get repository list',
      took: Math.round(endTime - startTime)
    };
  } catch (error) {
    const endTime = performance.now();
    console.error('getRepos error:', error);
    
    return {
      success: false,
      message: error.response?.data?.message || error.message || 'Failed to get repository list',
      stderr: error.response?.data?.detail || error.message,
      took: Math.round(endTime - startTime)
    };
  }
}

/**
 * Save GitHub Token
 * @param {string} token - GitHub Token
 * @param {string} proxy - Proxy URL (optional)
 * @returns {Promise<Object>} Save result
 */
export async function saveToken(token, proxy = '') {
  const trimmed = token.trim();
  if (!trimmed) {
    return { success: false, message: 'Token cannot be empty' };
  }
  
  const validationResult = await validateToken(trimmed, proxy);
  if (!validationResult.success) {
    return validationResult;
  }
  
  const startTime = performance.now();
  
  try {
    const response = await apiClient.post('/file/save/token', {
      token: trimmed
    });
    
    const endTime = performance.now();
    
    if (response.code === 0) {
      console.log('Token saved:', maskToken(trimmed));
      return {
        success: true,
        message: response.data.message,
        took: Math.round(endTime - startTime)
      };
    }
    
    return {
      success: false,
      message: response.data.message || 'Failed to save token',
      took: Math.round(endTime - startTime)
    };
  } catch (error) {
    const endTime = performance.now();
    console.error('saveToken error:', error);
    
    return {
      success: false,
      message: error.response?.data?.message || error.message || 'Failed to save token',
      stderr: error.response?.data?.detail || error.message,
      took: Math.round(endTime - startTime)
    };
  }
}

/**
 * Get branches from GitHub repository
 * @param {string} token - GitHub Token
 * @param {string} repo - Repository name
 * @param {string} proxy - Proxy URL (optional)
 * @returns {Promise<Object>} Branches result
 */
export async function getBranches(token, repo, proxy = '') {
  const trimmedToken = token.trim();
  const trimmedRepo = repo.trim();
  
  if (!trimmedToken) {
    return { success: false, message: 'Token cannot be empty' };
  }
  
  if (!trimmedRepo) {
    return { success: false, message: 'Repository name cannot be empty' };
  }
  
  const startTime = performance.now();
  
  try {
    console.log("GET_BRANCHES_SEND =", { token: maskToken(trimmedToken), repo: trimmedRepo });
    
    const response = await apiClient.get('/git/branches', {
      params: {
        token: trimmedToken,
        repo: trimmedRepo
      }
    });
    
    const endTime = performance.now();
    console.log("GET_BRANCHES_RECEIVE =", { response, took: `${(endTime - startTime).toFixed(2)}ms` });
    
    if (response.code === 0 && response.data) {
      return {
        success: true,
        branches: response.data.branches,
        default_branch: response.data.default_branch,
        took: Math.round(endTime - startTime)
      };
    }
    
    return {
      success: false,
      message: response.message || 'Failed to get branch list',
      took: Math.round(endTime - startTime)
    };
  } catch (error) {
    const endTime = performance.now();
    console.error("getBranches error:", error);
    
    return {
      success: false,
      message: error.response?.data?.message || error.message || 'Failed to get branch list',
      stderr: error.response?.data?.detail || error.message,
      took: Math.round(endTime - startTime)
    };
  }
}

/**
 * Create new branch on GitHub repository
 * @param {string} token - GitHub Token
 * @param {string} repo - Repository name
 * @param {string} branch - New branch name
 * @param {string} proxy - Proxy URL (optional)
 * @returns {Promise<Object>} Create result
 */
export async function createBranch(token, repo, branch, proxy = '') {
  const trimmedToken = token.trim();
  const trimmedRepo = repo.trim();
  const trimmedBranch = branch.trim();
  
  if (!trimmedToken) {
    return { success: false, message: 'Token cannot be empty' };
  }
  
  if (!trimmedRepo) {
    return { success: false, message: 'Repository name cannot be empty' };
  }
  
  if (!trimmedBranch) {
    return { success: false, message: 'Branch name cannot be empty' };
  }
  
  if (!/^[a-zA-Z0-9-_/]+$/.test(trimmedBranch)) {
    return { success: false, message: 'Branch name can only contain letters, numbers, -_/' };
  }
  
  const startTime = performance.now();
  
  try {
    console.log("CREATE_BRANCH_SEND =", { token: maskToken(trimmedToken), repo: trimmedRepo, branch: trimmedBranch });
    
    const response = await apiClient.post('/create/branch', {
      token: trimmedToken,
      repo: trimmedRepo,
      branch: trimmedBranch
    });
    
    const endTime = performance.now();
    console.log("CREATE_BRANCH_RECEIVE =", { response, took: `${(endTime - startTime).toFixed(2)}ms` });
    
    if (response.code === 0 && response.data) {
      return {
        success: true,
        message: response.data.message,
        branch_name: response.data.branch_name,
        took: Math.round(endTime - startTime)
      };
    }
    
    return {
      success: false,
      message: response.data.message || 'Failed to create branch',
      took: Math.round(endTime - startTime)
    };
  } catch (error) {
    const endTime = performance.now();
    console.error("createBranch error:", error);
    
    return {
      success: false,
      message: error.response?.data?.message || error.message || 'Failed to create branch',
      stderr: error.response?.data?.detail || error.message,
      took: Math.round(endTime - startTime)
    };
  }
}

/**
 * Run Python upload process
 * @param {string} token - GitHub Token
 * @param {string} repo - Repository name
 * @param {string} branch - Branch name
 * @param {string|Array<string>} localPaths - Local path(s)
 * @param {string} proxy - Proxy URL (optional)
 * @param {string} conflictStrategy - Conflict strategy (optional)
 * @returns {Promise<Object>} Upload result
 */
export async function runPythonUpload(token, repo, branch, localPaths, proxy = '', conflictStrategy = 'overwrite', ignorePatterns = []) {
  const trimmedToken = token.trim();
  const trimmedRepo = repo.trim();
  const trimmedBranch = branch.trim();
  
  if (!trimmedToken) {
    return { success: false, message: 'Token cannot be empty' };
  }
  
  if (!trimmedRepo) {
    return { success: false, message: 'Repository name cannot be empty' };
  }
  
  if (!trimmedBranch) {
    return { success: false, message: 'Branch name cannot be empty' };
  }
  
  const pathsArray = Array.isArray(localPaths) ? localPaths : [localPaths];
  
  if (pathsArray.length === 0) {
    return { success: false, message: 'File path cannot be empty' };
  }
  
  let absPaths;
  try {
    absPaths = await Promise.all(pathsArray.map(path => resolve(path)));
  } catch (error) {
    return {
      success: false,
      message: 'Path resolution failed',
      stderr: error.message || 'Path resolution failed'
    };
  }
  
  const startTime = performance.now();
  
  try {
    console.log("UPLOAD_SEND =", { 
      token: maskToken(trimmedToken), 
      repo: trimmedRepo, 
      branch: trimmedBranch, 
      paths: absPaths, 
      proxy, 
      conflictStrategy 
    });
    const pushParams = {
      token: trimmedToken,
      repo: trimmedRepo,
      branch: trimmedBranch,
      filepaths: absPaths,
      conflict_strategy: conflictStrategy,
      ignore_patterns: Array.isArray(ignorePatterns) ? ignorePatterns : []
    };
    
    const pushResult = await startGitPush(pushParams);
    
    if (!pushResult.success || !pushResult.task_id) {
      return {
        success: false,
        message: pushResult.message || 'Failed to start Git push',
        took: Math.round(performance.now() - startTime)
      };
    }
    
    const taskId = pushResult.task_id;
    let finalStatus = null;
    let pollCount = 0;
    const maxPolls = 300;
    
    while (pollCount < maxPolls) {
      pollCount++;
      const statusResult = await getGitStatus(taskId);
      
      if (!statusResult.success) {
        return {
          success: false,
          message: statusResult.message || 'Failed to get Git status',
          took: Math.round(performance.now() - startTime)
        };
      }
      
      finalStatus = statusResult;
      
      if (statusResult.status === 'done') {
        break;
      }
      
      if (statusResult.status === 'error' || statusResult.status === 'canceled') {
        break;
      }
      
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    const endTime = performance.now();
    
    if (finalStatus.status === 'done') {
      return {
        success: true,
        url: `https://github.com/${trimmedRepo}`,
        statistics: {
          file_count: finalStatus.total_files_count,
          total_size_bytes: finalStatus.total_size_bytes,
          total_size_mb: finalStatus.total_size_bytes ? (finalStatus.total_size_bytes / 1024 / 1024).toFixed(2) : 0
        },
        pushed_sha: finalStatus.output?.match(/([a-f0-9]{40})/)?.[0] || '',
        head_sha: finalStatus.output?.match(/HEAD -> ([a-f0-9]+)/)?.[1] || '',
        remote_sha: finalStatus.output?.match(/([a-f0-9]{40})/)?.[0] || '',
        took: Math.round(endTime - startTime)
      };
    } else {
      return {
        success: false,
        message: finalStatus.error || `Upload failed with status: ${finalStatus.status}`,
        stderr: finalStatus.error || finalStatus.output,
        took: Math.round(endTime - startTime)
      };
    }
  } catch (error) {
    const endTime = performance.now();
    console.error("UPLOAD_ERROR =", { error, took: `${(endTime - startTime).toFixed(2)}ms` });
    
    return {
      success: false,
      message: error.message || 'Upload failed',
      stderr: error.response?.data?.detail || error.message,
      took: Math.round(endTime - startTime)
    };
  }
}

/**
 * Scan file or folder path using FastAPI backend
 * @param {string|Array<string>} paths - Local path(s) to scan
 * @returns {Promise<Object>} Scan result with count and size
 */
export async function scanPath(paths) {
  const pathsArray = Array.isArray(paths) ? paths : [paths];
  
  if (pathsArray.length === 0) {
    return { success: false, message: 'Path cannot be empty' };
  }
  
  const startTime = performance.now();
  
  try {
    console.log("SCAN_PATH_SEND =", { paths: pathsArray });
    
    const response = await apiClient.post('/file/scan', {
      path: pathsArray.length === 1 ? pathsArray[0] : pathsArray
    });
    
    const endTime = performance.now();
    console.log("SCAN_PATH_RECEIVE =", { response, took: `${(endTime - startTime).toFixed(2)}ms` });
    
    if (response.code === 0 && response.data) {
      return {
        success: true,
        ...response.data,
        took: Math.round(endTime - startTime)
      };
    }
    
    return {
      success: false,
      message: response.message || 'Failed to scan path',
      took: Math.round(endTime - startTime)
    };
  } catch (error) {
    const endTime = performance.now();
    console.error("SCAN_PATH_ERROR =", { error, took: `${(endTime - startTime).toFixed(2)}ms` });
    
    return {
      success: false,
      message: error.response?.data?.message || error.message || 'Failed to scan path',
      took: Math.round(endTime - startTime)
    };
  }
}

/**
 * Start Git push using FastAPI backend
 * @param {Object} params - Git push parameters
 * @returns {Promise<Object>} Push result with task_id
 */
export async function startGitPush(params) {
  const startTime = performance.now();
  
  try {
    console.log("GIT_PUSH_SEND =", { repo_path: params.repo_path, branch: params.branch });
    
    const response = await apiClient.post('/git/push', params);
    
    const endTime = performance.now();
    console.log("GIT_PUSH_RECEIVE =", { response, took: `${(endTime - startTime).toFixed(2)}ms` });
    
    if (response.code === 0 && response.data) {
      return {
        success: true,
        ...response.data,
        took: Math.round(endTime - startTime)
      };
    }
    
    return {
      success: false,
      message: response.message || 'Failed to start Git push',
      took: Math.round(endTime - startTime)
    };
  } catch (error) {
    const endTime = performance.now();
    console.error("GIT_PUSH_ERROR =", { error, took: `${(endTime - startTime).toFixed(2)}ms` });
    
    return {
      success: false,
      message: error.response?.data?.message || error.message || 'Failed to start Git push',
      took: Math.round(endTime - startTime)
    };
  }
}

/**
 * Get Git push status using FastAPI backend
 * @param {string} taskId - Task ID from push start
 * @returns {Promise<Object>} Status result
 */
export async function getGitStatus(taskId) {
  const startTime = performance.now();
  
  try {
    const response = await apiClient.get(`/git/status/${taskId}`);
    
    const endTime = performance.now();
    
    if (response.code === 0 && response.data) {
      return {
        success: true,
        ...response.data,
        took: Math.round(endTime - startTime)
      };
    }
    
    return {
      success: false,
      message: response.message || 'Failed to get Git status',
      took: Math.round(endTime - startTime)
    };
  } catch (error) {
    const endTime = performance.now();
    
    return {
      success: false,
      message: error.response?.data?.message || error.message || 'Failed to get Git status',
      took: Math.round(endTime - startTime)
    };
  }
}

/**
 * Cancel Git push using FastAPI backend
 * @param {string} taskId - Task ID to cancel
 * @returns {Promise<Object>} Cancel result
 */
export async function cancelGitPush(taskId) {
  const startTime = performance.now();
  
  try {
    const response = await apiClient.post(`/git/cancel/${taskId}`);
    
    const endTime = performance.now();
    
    if (response.success) {
      return {
        success: true,
        took: Math.round(endTime - startTime)
      };
    }
    
    return {
      success: false,
      message: response.message || 'Failed to cancel Git push',
      took: Math.round(endTime - startTime)
    };
  } catch (error) {
    const endTime = performance.now();
    
    return {
      success: false,
      message: error.response?.data?.message || error.message || 'Failed to cancel Git push',
      took: Math.round(endTime - startTime)
    };
  }
}

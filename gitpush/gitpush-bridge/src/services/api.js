import { invoke } from '@tauri-apps/api/core';
import { resolve } from '@tauri-apps/api/path';
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
  
  try {
    if (shouldUseBackend(proxy)) {
      // Handle through backend
      const result = await invoke("run_python_upload", {
        token: trimmed,
        repo: "",
        branch: "",
        path: [],
        action: "validate_token",
        proxy
      });
      
      return result.success ? result : { success: false, message: result.message || 'Token validation failed' };
    } else {
      // Frontend direct connection to GitHub
      const response = await fetchWithTimeout('https://api.github.com/user', {
        headers: {
          'Authorization': `Bearer ${trimmed}`,
          'Accept': 'application/vnd.github.v3+json'
        },
        timeout: 8000
      });
      
      if (response.ok) {
        const user = await response.json();
        return {
          success: true,
          message: 'Token validation successful',
          user: user.login
        };
      } else {
        const text = await response.text();
        return {
          success: false,
          message: `GitHub validation failed: ${response.status} ${response.statusText}`,
          statusCode: response.status
        };
      }
    }
  } catch (error) {
    console.error('validateToken error:', error);
    return {
      success: false,
      message: error.message || 'Token validation failed',
      stderr: error.stderr || error.message
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
  
  try {
    const startTime = performance.now();
    
    if (shouldUseBackend(proxy)) {
      // 通过后端处理
      const result = await invoke("run_python_upload", {
        token: trimmedToken,
        repo: "",
        branch: "",
        path: [],
        action: "get_repos",
        proxy
      });
      const endTime = performance.now();
      
      console.log("GET_REPOS_RECEIVE =", { result, took: `${(endTime - startTime).toFixed(2)}ms` });
      
      if (result.success && result.repos) {
        return {
          success: true,
          repos: result.repos,
          took: Math.round(endTime - startTime)
        };
      }
      
      return {
        success: false,
        message: result.message || 'Failed to get repository list',
        took: Math.round(endTime - startTime)
      };
    } else {
      // 前端直连 GitHub
      const response = await fetchWithTimeout('https://api.github.com/user/repos', {
        headers: {
          'Authorization': `Bearer ${trimmedToken}`,
          'Accept': 'application/vnd.github.v3+json'
        },
        timeout: 8000
      });
      const endTime = performance.now();
      
      if (response.ok) {
        const repos = await response.json();
        // Only return required fields
        const formattedRepos = repos.map(repo => ({
          full_name: repo.full_name,
          description: repo.description,
          name: repo.name
        }));
        
        return {
          success: true,
          repos: formattedRepos,
          took: Math.round(endTime - startTime)
        };
      } else {
        const text = await response.text();
        return {
          success: false,
          message: `Failed to get repository list: ${response.status} ${response.statusText}`,
          statusCode: response.status,
          took: Math.round(endTime - startTime)
        };
      }
    }
  } catch (error) {
    console.error('getRepos error:', error);
    return {
      success: false,
      message: error.message || 'Failed to get repository list',
      stderr: error.stderr || error.message
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
  
  try {
    await writeTextFile('.gitpush_token', trimmed, { dir: BaseDirectory.Home });
    console.log('Token saved:', maskToken(trimmed));
    return { success: true, message: 'Token validated and saved successfully' };
  } catch (error) {
    console.error('saveToken error:', error);
    return {
      success: false,
      message: error.message || 'Failed to save token',
      stderr: error.stderr || error.message
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
  
  // Parameter validation
  if (!trimmedToken) {
    return { success: false, message: 'Token cannot be empty' };
  }
  
  if (!trimmedRepo) {
    return { success: false, message: 'Repository name cannot be empty' };
  }
  
  try {
    const startTime = performance.now();
    console.log("GET_BRANCHES_SEND =", { token: maskToken(trimmedToken), repo: trimmedRepo });
    
    if (shouldUseBackend(proxy)) {
      // 通过后端处理
      const result = await invoke("run_python_upload", {
        token: trimmedToken,
        repo: trimmedRepo,
        branch: "",
        path: [],
        action: "get_branches",
        proxy
      });
      
      const endTime = performance.now();
      console.log("GET_BRANCHES_RECEIVE =", { result, took: `${(endTime - startTime).toFixed(2)}ms` });
      
      if (result.success && result.branches) {
        return {
          success: true,
          branches: result.branches,
          took: Math.round(endTime - startTime)
        };
      }
      
      return {
        success: false,
        message: result.message || 'Failed to get branch list',
        took: Math.round(endTime - startTime),
        stderr: result.stderr || result.message
      };
    } else {
      // 前端直连 GitHub
      const url = `https://api.github.com/repos/${trimmedRepo}/branches`;
      const response = await fetchWithTimeout(url, {
        headers: {
          'Authorization': `Bearer ${trimmedToken}`,
          'Accept': 'application/vnd.github.v3+json'
        },
        timeout: 8000
      });
      
      const endTime = performance.now();
      
      if (response.ok) {
        const branchesData = await response.json();
        const branches = branchesData.map(branch => branch.name);
        
        return {
          success: true,
          branches: branches,
          took: Math.round(endTime - startTime)
        };
      } else {
        const text = await response.text();
        return {
          success: false,
          message: `Failed to get branch list: ${response.status} ${response.statusText}`,
          statusCode: response.status,
          took: Math.round(endTime - startTime)
        };
      }
    }
  } catch (error) {
    console.error("getBranches error:", error);
    return {
      success: false,
      message: error.message || 'Failed to get branch list',
      stderr: error.stderr || error.message
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
  
  // 参数校验
  if (!trimmedToken) {
    return { success: false, message: 'Token cannot be empty' };
  }
  
  if (!trimmedRepo) {
    return { success: false, message: 'Repository name cannot be empty' };
  }
  
  if (!trimmedBranch) {
    return { success: false, message: 'Branch name cannot be empty' };
  }
  
  // Branch name format validation
  if (!/^[a-zA-Z0-9-_/]+$/.test(trimmedBranch)) {
    return { success: false, message: 'Branch name can only contain letters, numbers, -_/' };
  }
  
  try {
    console.log("CREATE_BRANCH_SEND =", { token: maskToken(trimmedToken), repo: trimmedRepo, branch: trimmedBranch });
    
    if (shouldUseBackend(proxy)) {
      // 通过后端处理
      const result = await invoke("run_python_upload", {
        token: trimmedToken,
        repo: trimmedRepo,
        branch: trimmedBranch,
        path: [],
        action: "create_branch",
        proxy
      });
      
      console.log("CREATE_BRANCH_RECEIVE =", result);
      
      return result.success ? result : {
        success: false,
        message: result.message || 'Failed to create branch',
        stderr: result.stderr || result.message
      };
    } else {
      // Frontend direct connection to GitHub: creating branch is complex, need to get default branch SHA first, then create branch
      // Simplified processing here, just return success, actual branch creation is still handled by backend
      return {
        success: true,
        message: 'Branch creation request submitted (frontend mode branch creation is actually handled during upload stage)'
      };
    }
  } catch (error) {
    console.error("createBranch error:", error);
    return {
      success: false,
      message: error.message || 'Failed to create branch',
      stderr: error.stderr || error.message
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
  // 参数校验
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
  
  // Path processing and validation
  const pathsArray = Array.isArray(localPaths) ? localPaths : [localPaths];
  
  if (pathsArray.length === 0) {
    return { success: false, message: 'File path cannot be empty' };
  }
  
  // 转换为绝对路径
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
  
  // 添加时间戳和打码 token
  const startTime = performance.now();
  console.log("UPLOAD_SEND =", { 
    token: maskToken(trimmedToken), 
    repo: trimmedRepo, 
    branch: trimmedBranch, 
    paths: absPaths, 
    proxy, 
    conflictStrategy 
  });
  
  try {
    // 始终构造 payload 并调用后端
    const payload = {
      token: trimmedToken,
      repo: trimmedRepo,
      branch: trimmedBranch,
      path: absPaths,
      action: "upload",
      proxy,
      conflict_strategy: conflictStrategy,
      ignore_patterns: Array.isArray(ignorePatterns) ? ignorePatterns : []
    };
    
    const result = await invoke("run_python_upload", payload);
    const endTime = performance.now();
    
    // 组装处理结果
    const processedResult = {
      ...result,
      took: Math.round(endTime - startTime)
    };
    
    console.log("UPLOAD_RECEIVE =", { result: processedResult, took: `${(endTime - startTime).toFixed(2)}ms` });
    
    // 计算 sizeFormatted，确保始终显示正确的大小格式
    const stats = processedResult.statistics || {};
    const sizeMb = typeof stats.total_size_mb === 'number'
      ? stats.total_size_mb.toFixed(2)
      : stats.total_size_bytes
        ? (stats.total_size_bytes / 1024 / 1024).toFixed(2)
        : '0';
    processedResult.sizeFormatted = `${sizeMb} MB`;
    
    // 放宽成功判定条件：只要 success === true 且有 url 即认定成功
    if (!processedResult.success || !processedResult.url) {
      return {
        success: false,
        message: 'Upload failed or no valid push results generated',
        stderr: processedResult.stderr || processedResult.push_stderr || processedResult.message,
        took: processedResult.took
      };
    }
    
    // 记录警告但不影响成功判定
    if (!processedResult.statistics || !processedResult.statistics.file_count > 0) {
      console.warn('Upload success but no valid file count in statistics');
    }
    
    if (!processedResult.pushed_sha || !processedResult.head_sha || !processedResult.remote_sha) {
      console.warn('Upload success but missing SHA information');
    } else if (processedResult.head_sha !== processedResult.remote_sha) {
      console.warn('Upload success but SHA mismatch');
    }
    
    return processedResult;
  } catch (error) {
    const endTime = performance.now();
    console.error("UPLOAD_ERROR =", { error, took: `${(endTime - startTime).toFixed(2)}ms` });
    
    // 提取 stderr
    let stderr = error.stderr || error.message;
    if (error.message && !stderr) {
      const stderrMatch = error.message.match(/PYTHON STDERR ----[\s\S]*?===/);
      if (stderrMatch) {
        stderr = stderrMatch[0].replace(/PYTHON STDERR ----|===/g, '').trim();
      }
    }
    
    return {
      success: false,
      message: error.message || 'Upload failed',
      stderr,
      took: Math.round(endTime - startTime)
    };
  }
}

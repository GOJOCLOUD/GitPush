const { invoke } = window.__TAURI__.core;

let tokenInputEl;
let repoInputEl;
let branchInputEl;
let pathInputEl;
let resultOutputEl;
let runUploadBtn;

async function runUpload() {
  try {
    // Get input values
    const token = tokenInputEl.value;
    const repo = repoInputEl.value;
    const branch = branchInputEl.value;
    const path = pathInputEl.value;
    
    // Call the Tauri command
    const result = await invoke("run_python_upload", {
      token,
      repo,
      branch,
      path
    });
    
    // Display the result in the pre tag
    resultOutputEl.textContent = JSON.stringify(result, null, 2);
  } catch (error) {
    // Handle any errors
    resultOutputEl.textContent = JSON.stringify({
      success: false,
      message: `Error: ${error.message}`
    }, null, 2);
  }
}

window.addEventListener("DOMContentLoaded", () => {
  // Get DOM elements
  tokenInputEl = document.getElementById("token-input");
  repoInputEl = document.getElementById("repo-input");
  branchInputEl = document.getElementById("branch-input");
  pathInputEl = document.getElementById("path-input");
  resultOutputEl = document.getElementById("result-output");
  runUploadBtn = document.getElementById("run-upload-btn");
  
  // Add event listener to the button
  runUploadBtn.addEventListener("click", runUpload);
});

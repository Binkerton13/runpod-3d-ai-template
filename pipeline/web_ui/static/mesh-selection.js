// Mesh file selection functions

// Load list of previously uploaded mesh files
async function loadUploadedMeshes() {
    try {
        const response = await fetch(`${API_BASE}/api/uploads/list?type=mesh`);
        const data = await response.json();
        
        const select = document.getElementById('previousMeshSelect');
        const group = document.getElementById('previousMeshGroup');
        
        if (!select || !group) return;
        
        // Clear existing options except first
        while (select.options.length > 1) {
            select.remove(1);
        }
        
        if (data.files && data.files.length > 0) {
            data.files.forEach(file => {
                const option = document.createElement('option');
                option.value = file.name;
                option.textContent = `${file.name} (${formatFileSize(file.size)})`;
                select.appendChild(option);
            });
            group.style.display = 'block';
        } else {
            group.style.display = 'none';
        }
    } catch (error) {
        console.error('Failed to load uploaded meshes:', error);
    }
}

// Select a previously uploaded mesh
async function selectPreviousMesh(filename) {
    if (!filename || !currentProject) return;
    
    try {
        // Load the mesh file from uploads folder
        const meshPath = `uploads/${filename}`;
        const response = await fetch(`/${meshPath}`);
        const blob = await response.blob();
        
        // Display file info
        displayFileInfo('mesh', {name: filename, size: blob.size});
        
        // Load into viewer
        const file = new File([blob], filename);
        await loadModelFile(file);
        
        // Show mesh type selector
        const meshTypeGroup = document.getElementById('meshTypeGroup');
        if (meshTypeGroup) {
            meshTypeGroup.style.display = 'block';
        }
        
        setStatus(`Loaded mesh: ${filename}`);
    } catch (error) {
        showError(`Failed to load mesh: ${error.message}`);
    }
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
}

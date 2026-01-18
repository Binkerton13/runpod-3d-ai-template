// 3D Character Pipeline - Web UI JavaScript

// Global state
let currentProject = null;
let scene, camera, renderer, controls;
let currentModel = null;
let wireframeMode = false;
let gridHelper = null;
const API_BASE = window.location.origin;
let currentTheme = null;
let promptLibrary = null;
let viewMode = '3d'; // '3d' or 'image'
let uploadedImages = [];
let styleReferences = [];
let poseReferences = [];
let generatedTextures = [];
let materialViewEnabled = false;
let loadedTextures = null;
let animationMixer = null;
let animationClip = null;
let isAnimationPlaying = false;
let animationClock = new THREE.Clock();
let currentMeshType = 'skeletal'; // 'skeletal' or 'static'

// ===================================
// Initialization
// ===================================

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initViewer3D();
    loadProjects();
    loadPromptLibrary();
    checkSystemStatus();
    setInterval(checkSystemStatus, 30000); // Check every 30s
});

// ===================================
// 3D Viewer Setup
// ===================================

function initViewer3D() {
    const container = document.getElementById('viewer3d');
    
    // Scene
    scene = new THREE.Scene();
    updateSceneBackground();
    
    // Camera
    camera = new THREE.PerspectiveCamera(
        50,
        container.clientWidth / container.clientHeight,
        0.1,
        1000
    );
    camera.position.set(3, 2, 3);
    
    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);
    
    // Controls
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    
    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(5, 10, 5);
    directionalLight.castShadow = true;
    scene.add(directionalLight);
    
    const directionalLight2 = new THREE.DirectionalLight(0x4a9eff, 0.3);
    directionalLight2.position.set(-5, 5, -5);
    scene.add(directionalLight2);
    
    // Grid
    createGrid();
    scene.add(gridHelper);
    
    // Handle window resize
    window.addEventListener('resize', onWindowResize);
    
    // Animation loop
    animate();
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    
    // Update animation mixer if playing
    if (animationMixer && isAnimationPlaying) {
        const delta = animationClock.getDelta();
        animationMixer.update(delta);
        updateAnimationUI();
    }
    
    renderer.render(scene, camera);
}

function onWindowResize() {
    const container = document.getElementById('viewer3d');
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
}

// ===================================
// Theme Management
// ===================================

function initTheme() {
    // Check localStorage first, then system preference
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme) {
        currentTheme = savedTheme;
    } else {
        currentTheme = prefersDark ? 'dark' : 'light';
    }
    
    applyTheme(currentTheme);
    
    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            currentTheme = e.matches ? 'dark' : 'light';
            applyTheme(currentTheme);
        }
    });
}

function toggleTheme() {
    currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
    applyTheme(currentTheme);
    localStorage.setItem('theme', currentTheme);
}

function applyTheme(theme) {
    if (theme === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
        document.getElementById('themeIcon').textContent = '☀️';
    } else {
        document.documentElement.removeAttribute('data-theme');
        document.getElementById('themeIcon').textContent = '🌙';
    }
    
    // Update 3D scene if initialized
    if (scene) {
        updateSceneBackground();
        updateGridColors();
    }
}

function updateSceneBackground() {
    const bgColor = getComputedStyle(document.documentElement)
        .getPropertyValue('--three-bg').trim();
    scene.background = new THREE.Color(bgColor);
}

function createGrid() {
    const primaryColor = getComputedStyle(document.documentElement)
        .getPropertyValue('--grid-primary').trim();
    const secondaryColor = getComputedStyle(document.documentElement)
        .getPropertyValue('--grid-secondary').trim();
    
    gridHelper = new THREE.GridHelper(
        10, 10,
        new THREE.Color(primaryColor),
        new THREE.Color(secondaryColor)
    );
}

function updateGridColors() {
    if (gridHelper) {
        scene.remove(gridHelper);
        createGrid();
        scene.add(gridHelper);
    }
}

// ===================================
// 3D Model Loading
// ===================================

function loadModelIntoViewer(file) {
    const fileExtension = file.name.split('.').pop().toLowerCase();
    const reader = new FileReader();
    
    reader.onload = (e) => {
        // Remove existing model
        if (currentModel) {
            scene.remove(currentModel);
        }
        
        if (fileExtension === 'fbx') {
            const loader = new THREE.FBXLoader();
            loader.load(e.target.result, (fbx) => {
                setupModel(fbx, file.name);
            });
        } else if (fileExtension === 'obj') {
            const loader = new THREE.OBJLoader();
            loader.load(e.target.result, (obj) => {
                setupModel(obj, file.name);
            });
        }
    };
    
    reader.readAsDataURL(file);
}

function setupModel(model, filename) {
    currentModel = model;
    
    // Center and scale model
    const box = new THREE.Box3().setFromObject(model);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    
    const maxDim = Math.max(size.x, size.y, size.z);
    const scale = 2 / maxDim;
    model.scale.multiplyScalar(scale);
    
    model.position.sub(center.multiplyScalar(scale));
    
    // Add material
    model.traverse((child) => {
        if (child.isMesh) {
            child.material = new THREE.MeshStandardMaterial({
                color: 0x808080,
                metalness: 0.3,
                roughness: 0.7
            });
            child.castShadow = true;
            child.receiveShadow = true;
        }
    });
    
    scene.add(model);
    
    // Update stats
    updateModelStats(model);
    
    // Enable material view button
    const materialBtn = document.getElementById('materialViewBtn');
    if (materialBtn) {
        materialBtn.style.display = 'inline-block';
    }
    
    // Check for animations
    setupAnimation(model);
    
    // Reset camera
    resetCamera();
}

function updateModelStats(model) {
    let vertices = 0;
    let faces = 0;
    
    model.traverse((child) => {
        if (child.isMesh) {
            if (child.geometry.attributes.position) {
                vertices += child.geometry.attributes.position.count;
            }
            if (child.geometry.index) {
                faces += child.geometry.index.count / 3;
            }
        }
    });
    
    document.getElementById('vertexCount').textContent = `Vertices: ${vertices.toLocaleString()}`;
    document.getElementById('faceCount').textContent = `Faces: ${Math.floor(faces).toLocaleString()}`;
    document.getElementById('meshFormat').textContent = `Format: ${currentModel.type}`;
}

// ===================================
// Viewer Controls
// ===================================

function resetCamera() {
    camera.position.set(3, 2, 3);
    camera.lookAt(0, 0, 0);
    controls.target.set(0, 0, 0);
}

function toggleWireframe() {
    wireframeMode = !wireframeMode;
    if (currentModel) {
        currentModel.traverse((child) => {
            if (child.isMesh) {
                child.material.wireframe = wireframeMode;
            }
        });
    }
}

function toggleGrid() {
    gridHelper.visible = !gridHelper.visible;
}

function toggleViewMode() {
    viewMode = viewMode === '3d' ? 'image' : '3d';
    
    const viewer3d = document.getElementById('viewer3d');
    const imageViewer = document.getElementById('imageViewer');
    const viewModeToggle = document.getElementById('viewModeToggle');
    const viewerTitle = document.getElementById('viewerTitle');
    const imageTypeSelector = document.getElementById('imageTypeSelector');
    
    // Toggle 3D-specific controls
    const btn3dControls = ['resetViewBtn', 'wireframeBtn', 'gridBtn'];
    btn3dControls.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.style.display = viewMode === '3d' ? 'inline-block' : 'none';
    });
    
    // Toggle viewer info
    const meshInfo = ['vertexCount', 'faceCount', 'meshFormat'];
    const imageInfo = ['imageCount'];
    
    meshInfo.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = viewMode === '3d' ? 'inline' : 'none';
    });
    
    imageInfo.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = viewMode === 'image' ? 'inline' : 'none';
    });
    
    if (viewMode === '3d') {
        viewer3d.style.display = 'block';
        imageViewer.style.display = 'none';
        imageTypeSelector.style.display = 'none';
        viewModeToggle.textContent = '🖼️ Image View';
        viewerTitle.textContent = '🎨 Model Viewer';
    } else {
        viewer3d.style.display = 'none';
        imageViewer.style.display = 'block';
        imageTypeSelector.style.display = 'inline-block';
        viewModeToggle.textContent = '📦 3D View';
        
        // Update based on current selector value
        const currentType = imageTypeSelector.value;
        switchImageType(currentType);
    }
}

function loadImageToViewer(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        uploadedImages.push({
            name: file.name,
            url: e.target.result
        });
        displayImagesInViewer();
    };
    reader.readAsDataURL(file);
}

function displayImagesInViewer() {
    const grid = document.getElementById('imageViewerGrid');
    grid.innerHTML = '';
    
    uploadedImages.forEach((img, index) => {
        const item = document.createElement('div');
        item.className = 'image-grid-item';
        item.onclick = () => showImageFullscreen(index);
        
        const image = document.createElement('img');
        image.src = img.url;
        image.alt = img.name;
        
        const label = document.createElement('div');
        label.className = 'image-label';
        label.textContent = img.name;
        
        item.appendChild(image);
        item.appendChild(label);
        grid.appendChild(item);
    });
    
    updateImageCount();
}

function switchImageType(type) {
    const viewerTitle = document.getElementById('viewerTitle');
    const grid = document.getElementById('imageViewerGrid');
    const single = document.getElementById('imageViewerSingle');
    
    // Reset to grid view
    grid.style.display = 'grid';
    single.style.display = 'none';
    
    // Update displayed images based on type
    let imagesToShow = [];
    let title = '';
    
    switch(type) {
        case 'udim':
            imagesToShow = uploadedImages.filter(img => !img.type || img.type === 'udim');
            title = '🖼️ UDIM Tiles';
            break;
        case 'style':
            imagesToShow = styleReferences;
            title = '🎨 Style References';
            break;
        case 'pose':
            imagesToShow = poseReferences;
            title = '🧘 Pose References';
            break;
        case 'textures':
            loadGeneratedTextures();
            imagesToShow = generatedTextures;
            title = '✨ Generated Textures';
            break;
    }
    
    viewerTitle.textContent = title;
    
    // Display images
    grid.innerHTML = '';
    
    if (imagesToShow.length === 0) {
        const emptyMsg = document.createElement('div');
        emptyMsg.style.gridColumn = '1 / -1';
        emptyMsg.style.textAlign = 'center';
        emptyMsg.style.padding = '2rem';
        emptyMsg.style.color = 'var(--text-secondary)';
        emptyMsg.textContent = `No ${type} images uploaded yet`;
        grid.appendChild(emptyMsg);
    } else {
        imagesToShow.forEach((img, index) => {
            const item = document.createElement('div');
            item.className = 'image-grid-item';
            item.onclick = () => showImageFullscreenByType(type, index);
            
            const image = document.createElement('img');
            image.src = img.url;
            image.alt = img.name;
            
            const label = document.createElement('div');
            label.className = 'image-label';
            label.textContent = img.name;
            
            item.appendChild(image);
            item.appendChild(label);
            grid.appendChild(item);
        });
    }
    
    // Update count
    const countEl = document.getElementById('imageCount');
    if (countEl) {
        countEl.textContent = `Images: ${imagesToShow.length}`;
    }
}

function showImageFullscreenByType(type, index) {
    const grid = document.getElementById('imageViewerGrid');
    const single = document.getElementById('imageViewerSingle');
    const img = document.getElementById('imageViewerImg');
    
    let imagesToShow = [];
    switch(type) {
        case 'udim':
            imagesToShow = uploadedImages.filter(img => !img.type || img.type === 'udim');
            break;
        case 'style':
            imagesToShow = styleReferences;
            break;
        case 'pose':
            imagesToShow = poseReferences;
            break;
    }
    
    if (grid.style.display === 'none') {
        // Back to grid
        switchImageType(type);
    } else {
        // Show single
        img.src = imagesToShow[index].url;
        img.alt = imagesToShow[index].name;
        grid.style.display = 'none';
        single.style.display = 'flex';
        
        // Click image to go back to grid
        single.onclick = () => {
            switchImageType(type);
        };
    }
}

function showImageFullscreen(index) {
    const grid = document.getElementById('imageViewerGrid');
    const single = document.getElementById('imageViewerSingle');
    const img = document.getElementById('imageViewerImg');
    
    if (grid.style.display === 'none') {
        // Back to grid
        grid.style.display = 'grid';
        single.style.display = 'none';
    } else {
        // Show single
        img.src = uploadedImages[index].url;
        img.alt = uploadedImages[index].name;
        grid.style.display = 'none';
        single.style.display = 'flex';
        
        // Click image to go back to grid
        single.onclick = () => {
            grid.style.display = 'grid';
            single.style.display = 'none';
        };
    }
}

function updateImageCount() {
    const countEl = document.getElementById('imageCount');
    if (countEl) {
        countEl.textContent = `Images: ${uploadedImages.length}`;
    }
}

function addReferenceImage(file, type) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const refData = {
            name: file.name,
            url: e.target.result,
            type: type
        };
        
        if (type === 'style') {
            styleReferences.push(refData);
            updateReferenceList('styleRefList', styleReferences);
        } else if (type === 'pose') {
            poseReferences.push(refData);
            updateReferenceList('poseRefList', poseReferences);
        }
        
        updateReferenceCounts();
    };
    reader.readAsDataURL(file);
}

function updateReferenceList(listId, references) {
    const list = document.getElementById(listId);
    if (!list) return;
    
    list.innerHTML = '';
    references.forEach((ref, index) => {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `
            <span>${ref.name}</span>
            <span class="file-item-remove" onclick="removeReference('${ref.type}', ${index})">×</span>
        `;
        list.appendChild(item);
    });
}

function removeReference(type, index) {
    if (type === 'style') {
        styleReferences.splice(index, 1);
        updateReferenceList('styleRefList', styleReferences);
    } else if (type === 'pose') {
        poseReferences.splice(index, 1);
        updateReferenceList('poseRefList', poseReferences);
    }
    updateReferenceCounts();
}

function updateReferenceCounts() {
    const styleCount = document.getElementById('styleRefCount');
    const poseCount = document.getElementById('poseRefCount');
    
    if (styleCount) styleCount.textContent = `Style: ${styleReferences.length}`;
    if (poseCount) poseCount.textContent = `Pose: ${poseReferences.length}`;
}

// ===================================
// Material View & Texture Loading
// ===================================

async function toggleMaterialView() {
    if (!currentModel) {
        showError('No model loaded');
        return;
    }
    
    materialViewEnabled = !materialViewEnabled;
    const btn = document.getElementById('materialViewBtn');
    
    if (materialViewEnabled) {
        btn.textContent = '📦 Basic View';
        await loadAndApplyTextures();
    } else {
        btn.textContent = '🎨 Material View';
        applyBasicMaterial();
    }
}

async function loadAndApplyTextures() {
    if (!currentProject) {
        showError('No project selected');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/projects/${currentProject}/textures`);
        const data = await response.json();
        
        if (data.status !== 'success' || !data.textures) {
            showError('No generated textures found');
            return;
        }
        
        const textureLoader = new THREE.TextureLoader();
        const textures = data.textures;
        
        const materialProps = {
            metalness: 0.3,
            roughness: 0.7
        };
        
        // Load available texture maps
        if (textures.albedo) {
            materialProps.map = textureLoader.load(`${API_BASE}${textures.albedo}`);
        }
        if (textures.normal) {
            materialProps.normalMap = textureLoader.load(`${API_BASE}${textures.normal}`);
        }
        if (textures.roughness) {
            materialProps.roughnessMap = textureLoader.load(`${API_BASE}${textures.roughness}`);
        }
        if (textures.metallic) {
            materialProps.metalnessMap = textureLoader.load(`${API_BASE}${textures.metallic}`);
        }
        if (textures.ao) {
            materialProps.aoMap = textureLoader.load(`${API_BASE}${textures.ao}`);
        }
        
        // Apply to model
        currentModel.traverse((child) => {
            if (child.isMesh) {
                child.material = new THREE.MeshStandardMaterial(materialProps);
                child.material.needsUpdate = true;
            }
        });
        
        showSuccess('Textures applied');
    } catch (error) {
        showError('Failed to load textures');
        console.error(error);
    }
}

function applyBasicMaterial() {
    if (!currentModel) return;
    
    currentModel.traverse((child) => {
        if (child.isMesh) {
            child.material = new THREE.MeshStandardMaterial({
                color: 0x808080,
                metalness: 0.3,
                roughness: 0.7
            });
            child.material.needsUpdate = true;
        }
    });
}

async function loadGeneratedTextures() {
    if (!currentProject) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/projects/${currentProject}/texture-list`);
        const data = await response.json();
        
        if (data.status === 'success' && data.files) {
            generatedTextures = data.files.map(file => ({
                name: file.name,
                url: `${API_BASE}${file.path}`,
                type: 'texture'
            }));
        }
    } catch (error) {
        console.error('Failed to load texture list:', error);
    }
}

// ===================================
// Animation Playback
// ===================================

function setupAnimation(model) {
    if (model.animations && model.animations.length > 0) {
        animationMixer = new THREE.AnimationMixer(model);
        animationClip = model.animations[0];
        const action = animationMixer.clipAction(animationClip);
        action.play();
        isAnimationPlaying = false;
        action.paused = true;
        
        // Show animation controls
        const animControls = document.getElementById('animControls');
        if (animControls) {
            animControls.style.display = 'flex';
        }
        
        // Setup slider
        const slider = document.getElementById('animSlider');
        if (slider) {
            slider.max = animationClip.duration;
            slider.value = 0;
        }
    }
}

function toggleAnimation() {
    if (!animationMixer) return;
    
    isAnimationPlaying = !isAnimationPlaying;
    const btn = document.getElementById('playPauseBtn');
    
    if (isAnimationPlaying) {
        btn.textContent = '⏸️';
        animationClock.start();
    } else {
        btn.textContent = '▶️';
    }
}

function seekAnimation(value) {
    if (!animationMixer || !animationClip) return;
    
    const action = animationMixer._actions[0];
    action.time = parseFloat(value);
    animationMixer.update(0);
}

function updateAnimationUI() {
    if (!animationMixer || !animationClip) return;
    
    const action = animationMixer._actions[0];
    const currentTime = action.time;
    const duration = animationClip.duration;
    
    const slider = document.getElementById('animSlider');
    const timeDisplay = document.getElementById('animTime');
    
    if (slider) {
        slider.value = currentTime;
    }
    
    if (timeDisplay) {
        const current = formatTime(currentTime);
        const total = formatTime(duration);
        timeDisplay.textContent = `${current} / ${total}`;
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// ===================================
// Mesh Type & Pipeline Control
// ===================================

function updateMeshType(type) {
    currentMeshType = type;
    
    // Show/hide rigging and animation sections
    const rigSection = document.querySelector('.config-section h3');
    const animSection = document.getElementById('spriteSection');
    
    const sections = document.querySelectorAll('.config-section');
    sections.forEach(section => {
        const heading = section.querySelector('h3');
        if (heading) {
            const text = heading.textContent.toLowerCase();
            if (type === 'static') {
                if (text.includes('rigging') || text.includes('animation')) {
                    section.style.opacity = '0.5';
                    section.style.pointerEvents = 'none';
                    const inputs = section.querySelectorAll('input, select, textarea, button');
                    inputs.forEach(input => input.disabled = true);
                }
            } else {
                section.style.opacity = '1';
                section.style.pointerEvents = 'auto';
                const inputs = section.querySelectorAll('input, select, textarea, button');
                inputs.forEach(input => input.disabled = false);
            }
        }
    });
    
    // Sprite generation only available for skeletal meshes
    if (animSection) {
        if (type === 'static') {
            animSection.style.display = 'none';
        } else {
            animSection.style.display = 'block';
        }
    }
    
    showSuccess(`Mesh type set to: ${type}`);
}

function toggleSpriteOptions(enabled) {
    const spriteOptions = document.getElementById('spriteOptions');
    if (spriteOptions) {
        spriteOptions.style.display = enabled ? 'block' : 'none';
    }
}

// ===================================
// File Upload Handling
// ===================================

function handleDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('drag-over');
}

function handleDragLeave(event) {
    event.currentTarget.classList.remove('drag-over');
}

function handleDrop(event, type) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
        processFiles(files, type);
    }
}

function handleFileSelect(event, type) {
    const files = event.target.files;
    if (files.length > 0) {
        processFiles(files, type);
    }
}

function processFiles(files, type) {
    if (!currentProject) {
        showError('Please select or create a project first');
        return;
    }
    
    switch(type) {
        case 'mesh':
            if (files.length > 0) {
                uploadFile(files[0], type);
                loadModelIntoViewer(files[0]);
                if (viewMode !== '3d') {
                    toggleViewMode();
                }
                // Show mesh type selector
                const meshTypeGroup = document.getElementById('meshTypeGroup');
                if (meshTypeGroup) {
                    meshTypeGroup.style.display = 'block';
                }
            }
            break;
        case 'udim':
            Array.from(files).forEach(file => {
                uploadFile(file, type);
                loadImageToViewer(file);
            });
            if (viewMode !== 'image') {
                toggleViewMode();
            }
            break;
        case 'style_reference':
            Array.from(files).forEach(file => {
                uploadFile(file, type);
                addReferenceImage(file, 'style');
            });
            break;
        case 'pose_reference':
            Array.from(files).forEach(file => {
                uploadFile(file, type);
                addReferenceImage(file, 'pose');
            });
            break;
        case 'reference':
            Array.from(files).forEach(file => uploadFile(file, type));
            break;
    }
}

async function uploadFile(file, type) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', type);
    formData.append('project', currentProject);
    
    try {
        showUploadProgress(true, `Uploading ${file.name}...`);
        
        const response = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showUploadProgress(false);
            updateFileDisplay(file, type);
            showSuccess(`Uploaded ${file.name}`);
        } else {
            showError(`Upload failed: ${result.message}`);
        }
    } catch (error) {
        showError(`Upload error: ${error.message}`);
    }
}

function updateFileDisplay(file, type) {
    if (type === 'mesh') {
        const info = document.getElementById('meshInfo');
        info.style.display = 'block';
        info.textContent = `✓ ${file.name} (${formatFileSize(file.size)})`;
    } else if (type === 'udim') {
        const list = document.getElementById('udimList');
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `
            <span>${file.name}</span>
            <span class="file-item-remove" onclick="removeFile('${file.name}', 'udim')">✕</span>
        `;
        list.appendChild(item);
    }
}

function showUploadProgress(show, text = '') {
    const progress = document.getElementById('uploadProgress');
    const progressText = document.getElementById('progressText');
    
    if (show) {
        progress.style.display = 'block';
        progressText.textContent = text;
    } else {
        progress.style.display = 'none';
    }
}

// ===================================
// Project Management
// ===================================

async function loadProjects() {
    try {
        const response = await fetch(`${API_BASE}/api/projects`);
        const data = await response.json();
        
        const select = document.getElementById('projectSelect');
        select.innerHTML = '<option value="">Select Project...</option>';
        
        data.projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.name;
            option.textContent = project.name;
            select.appendChild(option);
        });
    } catch (error) {
        showError('Failed to load projects');
    }
}

async function loadProject(projectName) {
    if (!projectName) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/projects/${projectName}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            currentProject = projectName;
            document.getElementById('projectNameInput').value = projectName;
            
            // Load config if available
            if (data.config) {
                loadConfigIntoForm(data.config);
            }
            
            setStatus(`Loaded project: ${projectName}`);
        }
    } catch (error) {
        showError('Failed to load project');
    }
}

function loadConfigIntoForm(config) {
    // Texture settings
    if (config.udim_tiles && config.udim_tiles['1001']) {
        document.getElementById('texturePrompt').value = config.udim_tiles['1001'].prompt || '';
        document.getElementById('textureNegative').value = config.udim_tiles['1001'].negative || '';
        document.getElementById('textureSeed').value = config.udim_tiles['1001'].seed || 12345;
    }
    
    // Rig settings
    if (config.unirig) {
        document.getElementById('rigScale').value = config.unirig.scale || 1.0;
        document.getElementById('rigOrientation').value = config.unirig.orientation || 'Y_UP';
    }
}

function showNewProjectDialog() {
    document.getElementById('newProjectModal').classList.add('active');
    document.getElementById('newProjectName').focus();
}

function closeModal() {
    document.getElementById('newProjectModal').classList.remove('active');
}

async function createNewProject() {
    const projectName = document.getElementById('newProjectName').value.trim();
    
    if (!projectName) {
        showError('Please enter a project name');
        return;
    }
    
    // Validate project name
    if (!/^[a-zA-Z0-9_-]+$/.test(projectName)) {
        showError('Project name can only contain letters, numbers, underscores, and hyphens');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/projects/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_name: projectName })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            closeModal();
            showSuccess(`Project "${projectName}" created`);
            await loadProjects();
            document.getElementById('projectSelect').value = projectName;
            loadProject(projectName);
        } else {
            showError(data.message);
        }
    } catch (error) {
        showError('Failed to create project');
    }
}

// ===================================
// Configuration
// ===================================

async function saveConfig() {
    if (!currentProject) {
        showError('No project selected');
        return;
    }
    
    const config = {
        project_name: currentProject,
        mesh_type: currentMeshType,
        udim_tiles: {
            "1001": {
                prompt: document.getElementById('texturePrompt').value,
                negative: document.getElementById('textureNegative').value,
                seed: parseInt(document.getElementById('textureSeed').value)
            }
        },
        unirig: {
            scale: parseFloat(document.getElementById('rigScale').value),
            orientation: document.getElementById('rigOrientation').value,
            enabled: currentMeshType === 'skeletal'
        },
        hy_motion_prompt: {
            category: document.getElementById('promptCategory').value,
            preset: document.getElementById('promptSelect').value,
            motion: document.getElementById('motionField').value,
            style: document.getElementById('styleField').value,
            constraints: document.getElementById('constraintsField').value,
            camera: document.getElementById('cameraField').value,
            output: document.getElementById('outputField').value,
            enabled: currentMeshType === 'skeletal'
        },
        sprite_generation: {
            enabled: document.getElementById('enableSprites')?.checked || false,
            frame_interval: parseInt(document.getElementById('spriteFrameInterval')?.value || 2),
            angles: Array.from(document.getElementById('spriteAngles')?.selectedOptions || []).map(opt => opt.value),
            character_prompt: document.getElementById('spriteCharacterPrompt')?.value || '',
            negative_prompt: document.getElementById('spriteNegativePrompt')?.value || '',
            resolution: parseInt(document.getElementById('spriteResolution')?.value || 768),
            generate_spritesheet: document.getElementById('spriteSpritesheet')?.checked || true
        },
        export_formats: {
            fbx: document.getElementById('exportFBX').checked,
            gltf: document.getElementById('exportGLTF').checked,
            usd: document.getElementById('exportUSD').checked
        }
    };
    
    try {
        const response = await fetch(`${API_BASE}/api/projects/${currentProject}/config`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showSuccess('Configuration saved');
        } else {
            showError('Failed to save configuration');
        }
    } catch (error) {
        showError('Failed to save configuration');
    }
}

// ===================================
// Pipeline Execution
// ===================================

async function startPipeline() {
    if (!currentProject) {
        showError('No project selected');
        return;
    }
    
    // Save config first
    await saveConfig();
    
    // Show pipeline modal
    showPipelineProgress();
    
    try {
        const response = await fetch(`${API_BASE}/api/pipeline/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project: currentProject })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showSuccess('Pipeline started');
            monitorPipeline(data.job_id);
        } else {
            showError('Failed to start pipeline');
        }
    } catch (error) {
        showError('Failed to start pipeline');
    }
}

function showPipelineProgress() {
    const modal = document.getElementById('pipelineModal');
    modal.classList.add('active');
    
    const steps = document.getElementById('pipelineSteps');
    steps.innerHTML = `
        <div class="pipeline-step active">
            <strong>1. Mesh Validation</strong>
            <p>Validating input mesh...</p>
        </div>
        <div class="pipeline-step">
            <strong>2. Texture Generation</strong>
            <p>Waiting...</p>
        </div>
        <div class="pipeline-step">
            <strong>3. Rigging</strong>
            <p>Waiting...</p>
        </div>
        <div class="pipeline-step">
            <strong>4. Animation</strong>
            <p>Waiting...</p>
        </div>
        <div class="pipeline-step">
            <strong>5. Export</strong>
            <p>Waiting...</p>
        </div>
    `;
}

function closePipelineModal() {
    document.getElementById('pipelineModal').classList.remove('active');
}

// ===================================
// Motion Prompt Library Management
// ===================================

async function loadPromptLibrary() {
    try {
        const response = await fetch('/pipeline/hy_motion_prompts/prompt_library.json');
        promptLibrary = await response.json();
        console.log('Prompt library loaded:', Object.keys(promptLibrary).length, 'categories');
    } catch (error) {
        console.error('Failed to load prompt library:', error);
        showError('Failed to load prompt library');
    }
}

function loadPromptCategory(category) {
    const promptSelectGroup = document.getElementById('promptSelectGroup');
    const promptSelect = document.getElementById('promptSelect');
    
    if (!category || category === 'custom') {
        promptSelectGroup.style.display = 'none';
        clearPromptFields();
        return;
    }
    
    if (!promptLibrary || !promptLibrary[category]) {
        showError('Category not found in library');
        return;
    }
    
    // Populate preset dropdown
    promptSelect.innerHTML = '<option value=\"\">Select preset...</option>';
    const categoryData = promptLibrary[category];
    
    Object.keys(categoryData).forEach(presetKey => {
        const option = document.createElement('option');
        option.value = presetKey;
        option.textContent = presetKey.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
        promptSelect.appendChild(option);
    });
    
    promptSelectGroup.style.display = 'block';
}

function loadPromptPreset(presetKey) {
    if (!presetKey) {
        clearPromptFields();
        return;
    }
    
    const category = document.getElementById('promptCategory').value;
    if (!promptLibrary || !promptLibrary[category] || !promptLibrary[category][presetKey]) {
        showError('Preset not found');
        return;
    }
    
    const preset = promptLibrary[category][presetKey];
    
    // Populate fields
    document.getElementById('motionField').value = preset.motion || '';
    document.getElementById('styleField').value = preset.style || '';
    document.getElementById('constraintsField').value = preset.constraints || '';
    document.getElementById('cameraField').value = preset.camera || 'Locked.';
    document.getElementById('outputField').value = preset.output || '30 frames, 30fps.';
    
    showSuccess(`Loaded preset: ${presetKey.replace(/_/g, ' ')}`);
}

function clearPromptFields() {
    document.getElementById('motionField').value = '';
    document.getElementById('styleField').value = '';
    document.getElementById('constraintsField').value = '';
    document.getElementById('cameraField').value = 'Locked.';
    document.getElementById('outputField').value = '30 frames, 30fps.';
}

// ===================================
// System Status
// ===================================

async function checkSystemStatus() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        
        document.getElementById('pipelineStatus').querySelector('.status-dot').classList.add('active');
    } catch (error) {
        document.getElementById('pipelineStatus').querySelector('.status-dot').classList.remove('active');
    }
}

// ===================================
// Utilities
// ===================================

function setStatus(message) {
    document.getElementById('statusText').textContent = message;
}

function showSuccess(message) {
    setStatus(`✓ ${message}`);
    setTimeout(() => setStatus('Ready'), 3000);
}

function showError(message) {
    setStatus(`✗ ${message}`);
    console.error(message);
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function removeFile(filename, type) {
    // Implementation for file removal
    console.log('Remove file:', filename, type);
}
// ===================================
// Pipeline Execution
// ===================================

async function runPipeline() {
    if (!currentProject) {
        showError('Please select a project first');
        return;
    }
    
    // Save config before running
    await saveConfig();
    
    const btn = document.getElementById('runPipelineBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Starting Pipeline...';
    
    try {
        const response = await fetch(`${API_BASE}/pipeline/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_name: currentProject
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccess('Pipeline started successfully');
            btn.textContent = '⏳ Pipeline Running...';
            
            // Show status section
            document.getElementById('pipelineStatus').style.display = 'block';
            
            // Start polling for status updates
            startPipelineStatusPolling();
        } else {
            showError(data.error || 'Failed to start pipeline');
            btn.disabled = false;
            btn.textContent = '▶️ Run Pipeline';
        }
    } catch (error) {
        showError('Error starting pipeline: ' + error.message);
        btn.disabled = false;
        btn.textContent = '▶️ Run Pipeline';
    }
}

let pipelineStatusInterval = null;

function startPipelineStatusPolling() {
    // Clear existing interval
    if (pipelineStatusInterval) {
        clearInterval(pipelineStatusInterval);
    }
    
    // Poll every 3 seconds
    pipelineStatusInterval = setInterval(refreshPipelineStatus, 3000);
    
    // Initial fetch
    refreshPipelineStatus();
}

function stopPipelineStatusPolling() {
    if (pipelineStatusInterval) {
        clearInterval(pipelineStatusInterval);
        pipelineStatusInterval = null;
    }
}

async function refreshPipelineStatus() {
    if (!currentProject) return;
    
    try {
        const response = await fetch(`${API_BASE}/pipeline/status/${currentProject}`);
        const data = await response.json();
        
        if (response.ok) {
            updatePipelineStatusDisplay(data);
            
            // Check if pipeline is complete
            const allComplete = Object.values(data.stages).every(stage => 
                !stage.required || stage.completed
            );
            
            if (allComplete) {
                stopPipelineStatusPolling();
                const btn = document.getElementById('runPipelineBtn');
                btn.disabled = false;
                btn.textContent = '✓ Pipeline Complete';
                setTimeout(() => {
                    btn.textContent = '▶️ Run Pipeline';
                }, 3000);
                
                // Load log
                loadPipelineLog();
            }
        }
    } catch (error) {
        console.error('Error fetching pipeline status:', error);
    }
}

function updatePipelineStatusDisplay(status) {
    const stagesDiv = document.getElementById('pipelineStages');
    if (!stagesDiv) return;
    
    let html = '<div class="stage-list">';
    
    const stageOrder = ['textures', 'rigging', 'animation', 'export', 'sprites'];
    
    for (const stageName of stageOrder) {
        const stage = status.stages[stageName];
        if (!stage) continue;
        
        let icon = '⏳';
        let statusClass = 'pending';
        
        if (stage.completed) {
            icon = '✅';
            statusClass = 'complete';
        } else if (!stage.required) {
            icon = '⊘';
            statusClass = 'skipped';
        }
        
        html += `
            <div class="stage-item ${statusClass}">
                <span class="stage-icon">${icon}</span>
                <span class="stage-name">${stage.name}</span>
                ${!stage.required ? '<small>(skipped)</small>' : ''}
            </div>
        `;
    }
    
    html += '</div>';
    stagesDiv.innerHTML = html;
}

async function loadPipelineLog() {
    if (!currentProject) return;
    
    try {
        const response = await fetch(`${API_BASE}/pipeline/log/${currentProject}?lines=50`);
        const data = await response.json();
        
        if (response.ok && data.log) {
            document.getElementById('logContent').textContent = data.log;
            document.getElementById('pipelineLog').style.display = 'block';
        }
    } catch (error) {
    }
}

// ===================================
// Model Management
// ===================================

let currentModels = {};
let currentWorkflow = 'texture_workflow';

function toggleModelManager() {
    document.getElementById('modelManagerModal').style.display = 'flex';
    loadModelsForType('checkpoints');
    validateModels();
}

function closeModelManager() {
    document.getElementById('modelManagerModal').style.display = 'none';
}

function switchModelTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    const tabs = {
        'browse': 'browseTab',
        'upload': 'uploadTab',
        'select': 'selectTab'
    };
    
    document.getElementById(tabs[tabName]).classList.add('active');
    
    if (tabName === 'browse') {
        loadModelsForType(document.getElementById('browseModelType').value);
    } else if (tabName === 'select') {
        loadWorkflowModels(document.getElementById('workflowSelect').value);
    }
}

async function loadModelsForType(modelType) {
    const modelList = document.getElementById('modelList');
    modelList.innerHTML = '<div class="loading">Loading models...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/api/models/list?type=${modelType}`);
        const data = await response.json();
        
        if (response.ok) {
            displayModelList(data.models, modelType);
        } else {
            modelList.innerHTML = `<div class="error">Error: ${data.error}</div>`;
        }
    } catch (error) {
        modelList.innerHTML = `<div class="error">Error loading models: ${error.message}</div>`;
    }
}

function displayModelList(models, modelType) {
    const modelList = document.getElementById('modelList');
    
    if (models.length === 0) {
        modelList.innerHTML = `
            <div class="empty-state">
                <p>📦 No ${modelType} models found</p>
                <p><small>Upload models in the Upload tab</small></p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="model-grid">';
    
    models.forEach(model => {
        html += `
            <div class="model-card">
                <div class="model-card-header">
                    <span class="model-icon">📦</span>
                    <span class="model-name" title="${model.name}">${model.name}</span>
                </div>
                <div class="model-card-body">
                    <div class="model-detail">
                        <span class="label">Size:</span>
                        <span class="value">${model.size_mb} MB</span>
                    </div>
                    <div class="model-detail">
                        <span class="label">Modified:</span>
                        <span class="value">${new Date(model.modified * 1000).toLocaleDateString()}</span>
                    </div>
                </div>
                <div class="model-card-actions">
                    <button class="btn btn-small" onclick="downloadModel('${modelType}', '${model.name}')">
                        ⬇️ Download
                    </button>
                    <button class="btn btn-small btn-danger" onclick="deleteModel('${modelType}', '${model.name}')">
                        🗑️ Delete
                    </button>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    modelList.innerHTML = html;
}

function refreshModelList() {
    const modelType = document.getElementById('browseModelType').value;
    loadModelsForType(modelType);
}

async function handleModelFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        await uploadModelFile(file);
    }
}

async function handleModelDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    
    const dropZone = event.currentTarget;
    dropZone.classList.remove('drag-over');
    
    const file = event.dataTransfer.files[0];
    if (file) {
        await uploadModelFile(file);
    }
}

async function uploadModelFile(file) {
    const modelType = document.getElementById('uploadModelType').value;
    const progressDiv = document.getElementById('modelUploadProgress');
    const progressFill = document.getElementById('modelProgressFill');
    const progressText = document.getElementById('modelProgressText');
    
    progressDiv.style.display = 'block';
    progressText.textContent = `Uploading ${file.name}...`;
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', modelType);
    
    try {
        const xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = (e.loaded / e.total) * 100;
                progressFill.style.width = percent + '%';
                progressText.textContent = `Uploading ${file.name}... ${Math.round(percent)}%`;
            }
        });
        
        xhr.addEventListener('load', async () => {
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                showSuccess(`Model uploaded: ${file.name}`);
                progressDiv.style.display = 'none';
                
                // Clear file input
                document.getElementById('modelFileInput').value = '';
                
                // Refresh model list if on browse tab
                if (document.getElementById('browseTab').classList.contains('active')) {
                    await loadModelsForType(modelType);
                }
                
                // Refresh validation
                await validateModels();
            } else {
                const data = JSON.parse(xhr.responseText);
                showError(data.error || 'Upload failed');
                progressDiv.style.display = 'none';
            }
        });
        
        xhr.addEventListener('error', () => {
            showError('Upload failed');
            progressDiv.style.display = 'none';
        });
        
        xhr.open('POST', `${API_BASE}/api/models/upload`);
        xhr.send(formData);
        
    } catch (error) {
        showError('Error uploading model: ' + error.message);
        progressDiv.style.display = 'none';
    }
}

async function deleteModel(modelType, filename) {
    if (!confirm(`Delete ${filename}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/models/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: modelType,
                filename: filename
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccess(data.message);
            await loadModelsForType(modelType);
            await validateModels();
        } else {
            showError(data.error || 'Delete failed');
        }
    } catch (error) {
        showError('Error deleting model: ' + error.message);
    }
}

function downloadModel(modelType, filename) {
    window.open(`${API_BASE}/api/models/download/${modelType}/${filename}`, '_blank');
}

async function loadWorkflowModels(workflowName) {
    currentWorkflow = workflowName;
    
    try {
        // Validate workflow
        const validationResponse = await fetch(`${API_BASE}/api/models/validate/${workflowName}`);
        const validation = await validationResponse.json();
        
        displayWorkflowValidation(validation);
        
        // Get current selections
        const selectionsResponse = await fetch(`${API_BASE}/api/models/selected/${workflowName}`);
        const selectionsData = await selectionsResponse.json();
        
        // Load all models
        const modelsResponse = await fetch(`${API_BASE}/api/models/list`);
        const modelsData = await modelsResponse.json();
        
        currentModels = modelsData.models;
        
        displayModelSelectors(workflowName, selectionsData.selected, validation);
        
    } catch (error) {
        showError('Error loading workflow models: ' + error.message);
    }
}

function displayWorkflowValidation(validation) {
    const validationDiv = document.getElementById('workflowValidation');
    
    if (validation.valid) {
        validationDiv.innerHTML = `
            <div class="validation-success">
                ✅ ${validation.message}
            </div>
        `;
    } else {
        let html = `
            <div class="validation-error">
                ⚠️ ${validation.message}
                <ul>
        `;
        
        validation.missing.forEach(missing => {
            html += `<li>${missing.description}</li>`;
        });
        
        html += `
                </ul>
                <p><small>Upload required models in the Upload tab or auto-select available models</small></p>
            </div>
        `;
        
        validationDiv.innerHTML = html;
    }
}

function displayModelSelectors(workflowName, selectedModels, validation) {
    const selectorsDiv = document.getElementById('modelSelectors');
    
    const requirements = {
        'texture_workflow': {
            'checkpoints': 'Base Model (SDXL)',
            'ipadapter': 'IP-Adapter'
        },
        'sprite_generation_workflow': {
            'checkpoints': 'Base Model (SDXL)',
            'controlnet': 'ControlNet (OpenPose/Depth)',
            'ipadapter': 'IP-Adapter'
        }
    };
    
    const workflowReqs = requirements[workflowName] || {};
    let html = '';
    
    for (const [modelType, label] of Object.entries(workflowReqs)) {
        const typeModels = currentModels[modelType] || [];
        const selectedModel = selectedModels[modelType] || '';
        
        html += `
            <div class="form-group">
                <label for="select_${modelType}">${label}</label>
                <select id="select_${modelType}" class="model-selector">
                    <option value="">-- Select ${modelType} --</option>
        `;
        
        typeModels.forEach(model => {
            const selected = model.name === selectedModel ? 'selected' : '';
            html += `<option value="${model.name}" ${selected}>${model.name} (${model.size_mb}MB)</option>`;
        });
        
        html += `
                </select>
                ${typeModels.length === 0 ? '<small class="error">⚠️ No models available - upload in Upload tab</small>' : ''}
            </div>
        `;
    }
    
    selectorsDiv.innerHTML = html;
}

async function autoSelectWorkflowModels() {
    const workflowName = document.getElementById('workflowSelect').value;
    
    try {
        const response = await fetch(`${API_BASE}/api/models/auto-select/${workflowName}`);
        const data = await response.json();
        
        if (response.ok) {
            showSuccess('Models auto-selected');
            
            // Update selectors
            for (const [modelType, modelName] of Object.entries(data.selected)) {
                const selector = document.getElementById(`select_${modelType}`);
                if (selector) {
                    selector.value = modelName;
                }
            }
        } else {
            showError(data.error || 'Auto-select failed');
        }
    } catch (error) {
        showError('Error auto-selecting models: ' + error.message);
    }
}

async function saveWorkflowModelSelections() {
    const workflowName = document.getElementById('workflowSelect').value;
    const selections = {};
    
    // Gather selections from dropdowns
    document.querySelectorAll('.model-selector').forEach(select => {
        const modelType = select.id.replace('select_', '');
        const value = select.value;
        if (value) {
            selections[modelType] = value;
        }
    });
    
    try {
        const response = await fetch(`${API_BASE}/api/models/selected/${workflowName}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ selections })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccess('Model selections saved');
            await validateModels();
        } else {
            showError(data.error || 'Save failed');
        }
    } catch (error) {
        showError('Error saving selections: ' + error.message);
    }
}

async function validateModels() {
    const workflows = ['texture_workflow', 'sprite_generation_workflow'];
    const validationDiv = document.getElementById('modelValidation');
    
    if (!validationDiv) return;
    
    validationDiv.style.display = 'block';
    
    for (const workflow of workflows) {
        try {
            const response = await fetch(`${API_BASE}/api/models/validate/${workflow}`);
            const validation = await response.json();
            
            const workflowId = workflow === 'texture_workflow' ? 'textureValidation' : 'spriteValidation';
            const element = document.getElementById(workflowId);
            
            if (element) {
                const icon = element.querySelector('.validation-icon');
                const text = element.querySelector('span:last-child');
                
                if (validation.valid) {
                    icon.textContent = '✅';
                    element.classList.remove('validation-error');
                    element.classList.add('validation-success');
                } else {
                    icon.textContent = '⚠️';
                    element.classList.remove('validation-success');
                    element.classList.add('validation-error');
                    element.title = validation.missing.map(m => m.description).join(', ');
                }
            }
        } catch (error) {
            console.error('Error validating workflow:', workflow, error);
        }
    }
}

// Initialize model validation on page load
document.addEventListener('DOMContentLoaded', () => {
    validateModels();
});

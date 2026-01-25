/* --------------------------------------------------
   MOTION PRESETS
-------------------------------------------------- */
async function loadPresets() {
    const res = await fetch("/api/motion/presets");
    const data = await res.json();

    const select = document.getElementById("motionPreset");
    select.innerHTML = "";

    data.presets.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p;
        opt.textContent = p;
        select.appendChild(opt);
    });
}

/* --------------------------------------------------
   MODEL MANAGER
-------------------------------------------------- */
async function loadModels() {
    const res = await fetch("/api/models");
    const data = await res.json();

    document.getElementById("modelOutput").textContent =
        JSON.stringify(data, null, 2);
}

/* --------------------------------------------------
   STYLE PRESETS
-------------------------------------------------- */
async function loadStyles() {
    const res = await fetch("/api/styles");
    const data = await res.json();

    const select = document.getElementById("stylePreset");
    select.innerHTML = "";

    Object.entries(data).forEach(([id, preset]) => {
        const opt = document.createElement("option");
        opt.value = id;
        opt.textContent = preset.label;
        select.appendChild(opt);
    });
}

/* --------------------------------------------------
   MOTION GENERATION
-------------------------------------------------- */
async function generateMotion() {
    const preset = document.getElementById("motionPreset").value;
    const seed = document.getElementById("motionSeed").value || null;

    const res = await fetch("/api/motion/generate", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ preset, seed })
    });

    const data = await res.json();
    document.getElementById("motionOutput").textContent =
        JSON.stringify(data, null, 2);
}

/* --------------------------------------------------
   PREVIEW VIDEO & FRAMES
-------------------------------------------------- */
async function previewVideo() {
    const path = document.getElementById("previewVideoPath").value;
    const video = document.getElementById("videoPlayer");

    video.src = `/api/preview/video?path=${encodeURIComponent(path)}`;
    video.style.display = "block";
    video.load();
}

async function previewFrames() {
    const dir = document.getElementById("previewFramesDir").value;
    const container = document.getElementById("frameContainer");

    container.innerHTML = "";

    const res = await fetch(`/api/preview/frames?dir=${encodeURIComponent(dir)}`);
    const data = await res.json();

    if (!data.frames) {
        container.innerHTML = "<p>No frames found.</p>";
        return;
    }

    data.frames.forEach(framePath => {
        const img = document.createElement("img");
        img.src = `/api/preview/frame?path=${encodeURIComponent(framePath)}`;
        img.width = 96;
        img.style.border = "1px solid var(--panel-border)";
        img.style.borderRadius = "4px";
        container.appendChild(img);
    });
}

/* --------------------------------------------------
   SPRITE GENERATION
-------------------------------------------------- */
async function generateSprites() {
    const character = document.getElementById("characterName").value;
    const frames_dir = document.getElementById("framesDir").value;
    const style = document.getElementById("stylePreset").value;

    const res = await fetch("/api/sprites/generate", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ character, frames_dir, style })
    });

    const data = await res.json();
    document.getElementById("spriteOutput").textContent =
        JSON.stringify(data, null, 2);
}

/* --------------------------------------------------
   SPRITE SHEET ASSEMBLY
-------------------------------------------------- */
async function assembleSheet() {
    const character = document.getElementById("sheetCharacter").value;
    const frames_dir = document.getElementById("sheetFramesDir").value;

    const res = await fetch("/api/sprites/assemble", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ character, frames_dir })
    });

    const data = await res.json();
    document.getElementById("sheetOutput").textContent =
        JSON.stringify(data, null, 2);
}

async function previewSheet() {
    const path = document.getElementById("sheetPreviewPath").value;
    const img = document.getElementById("sheetImage");

    img.src = `/api/preview/sheet?path=${encodeURIComponent(path)}`;
    img.style.display = "block";
}

/* --------------------------------------------------
   WORKFLOW EDITOR
-------------------------------------------------- */
async function loadWorkflowList() {
    const res = await fetch("/api/workflows");
    const data = await res.json();

    const select = document.getElementById("workflowSelect");
    select.innerHTML = "";

    data.workflows.forEach(name => {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        select.appendChild(opt);
    });
}

async function loadWorkflow() {
    const name = document.getElementById("workflowSelect").value;
    const res = await fetch(`/api/workflows/${name}`);
    const data = await res.json();

    document.getElementById("workflowEditor").value =
        JSON.stringify(data, null, 4);
}

async function saveWorkflow() {
    const name = document.getElementById("workflowSelect").value;
    const text = document.getElementById("workflowEditor").value;

    let jsonData;
    try {
        jsonData = JSON.parse(text);
    } catch (e) {
        document.getElementById("workflowOutput").textContent =
            "Invalid JSON: " + e.message;
        return;
    }

    const res = await fetch(`/api/workflows/${name}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(jsonData)
    });

    const data = await res.json();
    document.getElementById("workflowOutput").textContent =
        JSON.stringify(data, null, 2);
}

async function validateWorkflow() {
    const text = document.getElementById("workflowEditor").value;

    let jsonData;
    try {
        jsonData = JSON.parse(text);
    } catch (e) {
        document.getElementById("workflowOutput").textContent =
            "Invalid JSON: " + e.message;
        return;
    }

    const res = await fetch("/api/workflows/validate", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(jsonData)
    });

    const data = await res.json();
    document.getElementById("workflowOutput").textContent =
        JSON.stringify(data, null, 2);
}

/* --------------------------------------------------
   MODEL SELECTOR
-------------------------------------------------- */
async function loadModelSelectors() {
    const all = await (await fetch("/api/models")).json();
    const active = await (await fetch("/api/models/active")).json();

    const map = {
        selectCheckpoint: all.checkpoints,
        selectLora: all.loras,
        selectVae: all.vae,
        selectControlnet: all.controlnet,
        selectIpAdapter: all.unet
    };

    Object.entries(map).forEach(([id, list]) => {
        const select = document.getElementById(id);
        select.innerHTML = "";

        const empty = document.createElement("option");
        empty.value = "";
        empty.textContent = "(none)";
        select.appendChild(empty);

        list.forEach(file => {
            const opt = document.createElement("option");
            opt.value = file;
            opt.textContent = file;
            select.appendChild(opt);
        });
    });

    document.getElementById("selectCheckpoint").value = active.checkpoint || "";
    document.getElementById("selectLora").value = active.lora || "";
    document.getElementById("selectVae").value = active.vae || "";
    document.getElementById("selectControlnet").value = active.controlnet || "";
    document.getElementById("selectIpAdapter").value = active.ipadapter || "";
}

async function saveModelSelection() {
    const data = {
        checkpoint: document.getElementById("selectCheckpoint").value,
        lora: document.getElementById("selectLora").value,
        vae: document.getElementById("selectVae").value,
        controlnet: document.getElementById("selectControlnet").value,
        ipadapter: document.getElementById("selectIpAdapter").value
    };

    const res = await fetch("/api/models/active", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    });

    const out = await res.json();
    document.getElementById("modelSelectOutput").textContent =
        JSON.stringify(out, null, 2);
}

/* --------------------------------------------------
   BATCH GENERATOR
-------------------------------------------------- */
async function createBatch() {
    const motions = document.getElementById("batchMotions").value.split(",").map(s => s.trim()).filter(Boolean);
    const characters = document.getElementById("batchCharacters").value.split(",").map(s => s.trim()).filter(Boolean);
    const styles = document.getElementById("batchStyles").value.split(",").map(s => s.trim()).filter(Boolean);

    const res = await fetch("/api/batch/create", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ motions, characters, styles })
    });

    const data = await res.json();
    document.getElementById("batchOutput").textContent =
        JSON.stringify(data, null, 2);

    document.getElementById("batchId").value = data.batch_id;
}

async function runBatch() {
    const id = document.getElementById("batchId").value;

    const res = await fetch(`/api/batch/run/${id}`, {
        method: "POST"
    });

    const data = await res.json();
    document.getElementById("batchOutput").textContent =
        JSON.stringify(data, null, 2);
}

async function checkBatch() {
    const id = document.getElementById("batchId").value;

    const res = await fetch(`/api/batch/status/${id}`);
    const data = await res.json();

    document.getElementById("batchOutput").textContent =
        JSON.stringify(data, null, 2);

    const running = data.jobs && data.jobs.some(j =>
        j.status === "running" || j.status === "pending"
    );

    if (running) {
        setTimeout(checkBatch, 3000);
    }
}

/* --------------------------------------------------
   PROMPT TEMPLATES
-------------------------------------------------- */
async function loadPromptTemplates() {
    const res = await fetch("/api/prompts");
    const data = await res.json();

    const select = document.getElementById("promptTemplate");
    select.innerHTML = "";

    Object.entries(data).forEach(([id, tpl]) => {
        const opt = document.createElement("option");
        opt.value = id;
        opt.textContent = tpl.label;
        select.appendChild(opt);
    });
}

async function loadPromptTemplate() {
    const id = document.getElementById("promptTemplate").value;

    const res = await fetch(`/api/prompts/${id}`);
    const data = await res.json();

    document.getElementById("promptEditor").value =
        JSON.stringify(data, null, 4);
}

async function savePromptTemplate() {
    const id = document.getElementById("promptTemplate").value;
    const text = document.getElementById("promptEditor").value;

    let jsonData;
    try {
        jsonData = JSON.parse(text);
    } catch (e) {
        document.getElementById("promptOutput").textContent =
            "Invalid JSON: " + e.message;
        return;
    }

    const res = await fetch(`/api/prompts/${id}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(jsonData)
    });

    const data = await res.json();
    document.getElementById("promptOutput").textContent =
        JSON.stringify(data, null, 2);
}

/* --------------------------------------------------
   WORKFLOW NODE INSPECTOR
-------------------------------------------------- */
async function loadNodeWorkflowList() {
    const res = await fetch("/api/workflows");
    const data = await res.json();

    const select = document.getElementById("nodeWorkflowSelect");
    select.innerHTML = "";

    data.workflows.forEach(name => {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        select.appendChild(opt);
    });
}

async function loadNodeList() {
    const workflow = document.getElementById("nodeWorkflowSelect").value;

    const res = await fetch(`/api/workflows/nodes/${workflow}`);
    const data = await res.json();

    const select = document.getElementById("nodeSelect");
    select.innerHTML = "";

    data.nodes.forEach(node => {
        const opt = document.createElement("option");
        opt.value = node.id;
        opt.textContent = `${node.id} (${node.type || node.class_type || "Node"})`;
        select.appendChild(opt);
    });
}

async function loadNodeDetails() {
    const workflow = document.getElementById("nodeWorkflowSelect").value;
    const node = document.getElementById("nodeSelect").value;

    const res = await fetch(`/api/workflows/node/${workflow}/${node}`);
    const data = await res.json();

    document.getElementById("nodeOutput").textContent =
        JSON.stringify(data, null, 2);
}

/* --------------------------------------------------
   PROJECTS
-------------------------------------------------- */
async function loadProject() {
    const id = document.getElementById("projectId").value;

    const res = await fetch(`/api/project/load/${id}`);
    const data = await res.json();

    document.getElementById("projectOutput").textContent =
        JSON.stringify(data, null, 2);

    document.getElementById("projectName").value = data.name || "";

    // Motion
    document.getElementById("motionPreset").value = (data.motion && data.motion.preset) || "";
    document.getElementById("motionSeed").value = (data.motion && data.motion.seed) || "";

    // Sprite
    document.getElementById("characterName").value = (data.sprite && data.sprite.character) || "";
    document.getElementById("framesDir").value = (data.sprite && data.sprite.frames_dir) || "";
    document.getElementById("stylePreset").value = (data.sprite && data.sprite.style) || "";
    document.getElementById("promptTemplate").value = (data.sprite && data.sprite.prompt_template) || "";

    // Models
    document.getElementById("selectCheckpoint").value = (data.models && data.models.checkpoint) || "";
    document.getElementById("selectLora").value = (data.models && data.models.lora) || "";
    document.getElementById("selectVae").value = (data.models && data.models.vae) || "";
    document.getElementById("selectControlnet").value = (data.models && data.models.controlnet) || "";
    document.getElementById("selectIpAdapter").value = (data.models && data.models.ipadapter) || "";

    // Workflow
    document.getElementById("workflowSelect").value = (data.workflow && data.workflow.name) || "";
    document.getElementById("workflowEditor").value =
        JSON.stringify((data.workflow && data.workflow.json) || {}, null, 4);

    // Batch
    document.getElementById("batchMotions").value = (data.batch && data.batch.motions || []).join(",");
    document.getElementById("batchCharacters").value = (data.batch && data.batch.characters || []).join(",");
    document.getElementById("batchStyles").value = (data.batch && data.batch.styles || []).join(",");
}

async function listProjects() {
    const res = await fetch("/api/project/list");
    const data = await res.json();

    const select = document.getElementById("projectList");
    select.innerHTML = "";

    data.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.project_id;
        opt.textContent = `${p.project_id} — ${p.name}`;
        select.appendChild(opt);
    });

    document.getElementById("projectOutput").textContent =
        JSON.stringify(data, null, 2);
}

function loadSelectedProject() {
    const id = document.getElementById("projectList").value;
    document.getElementById("projectId").value = id;
    loadProject();
}

/* --------------------------------------------------
   INITIALIZATION
-------------------------------------------------- */
loadNodeWorkflowList();
loadPromptTemplates();
loadModelSelectors();
loadWorkflowList();
loadPresets();
loadStyles();
loadModels();
listProjects();

/* Commit trigger comment */
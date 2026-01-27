<template>
  <div class="graph-page">
    <h1 class="title">Workflow Graph</h1>

    <div class="graph-wrapper">
      <VueFlow
        v-model:nodes="store.nodes"
        v-model:edges="store.edges"
        class="graph"
        :node-types="{ workflowNode: WorkflowNode }"
        :fit-view="true"
        @node-click="onNodeClick"
        @contextmenu="onRightClick"
        @connect="onConnect"
      >
        <Controls />
        <MiniMap />
      </VueFlow>
    </div>

    <NodeCreateMenu
      :visible="showMenu"
      :position="menuPos"
      @close="showMenu = false"
      @create="createNode"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { VueFlow } from '@vue-flow/core'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { useWorkflowsStore } from '../stores/workflows'
import WorkflowNode from '../components/nodes/WorkflowNode.vue'
import NodeCreateMenu from '../components/nodes/NodeCreateMenu.vue'
import { useNotifyStore } from '../stores/notify'

/* -------------------------------------------------------
   STORES + STATE
------------------------------------------------------- */
const store = useWorkflowsStore()
const notify = useNotifyStore()

const showMenu = ref(false)
const menuPos = ref({ x: 0, y: 0 })
let lastClickedNode = null

/* -------------------------------------------------------
   DUMMY WORKFLOW (offline / empty state)
------------------------------------------------------- */
const dummyNodes = [
  {
    id: '1',
    type: 'workflowNode',
    position: { x: 150, y: 120 },
    data: { type: 'input', params: {}, inputs: [], outputs: [] }
  },
  {
    id: '2',
    type: 'workflowNode',
    position: { x: 450, y: 120 },
    data: { type: 'process', params: {}, inputs: [], outputs: [] }
  },
  {
    id: '3',
    type: 'workflowNode',
    position: { x: 750, y: 120 },
    data: { type: 'output', params: {}, inputs: [], outputs: [] }
  }
]

const dummyEdges = [
  { id: '1-2', source: '1', target: '2' },
  { id: '2-3', source: '2', target: '3' }
]

/* -------------------------------------------------------
   INIT
------------------------------------------------------- */
onMounted(() => {
  store.loadNodeTypes()

  // If backend is offline or store is empty, load dummy workflow
  if (store.nodes.length === 0 && store.edges.length === 0) {
    store.nodes = [...dummyNodes]
    store.edges = [...dummyEdges]
  }

  window.addEventListener('keydown', onKeyDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
})

/* -------------------------------------------------------
   CONNECTION VALIDATION
------------------------------------------------------- */
function onConnect(connection) {
  const sourceNode = store.nodes.find(n => n.id === connection.source)
  const targetNode = store.nodes.find(n => n.id === connection.target)
  if (!sourceNode || !targetNode) return

  const valid = store.validateConnection(sourceNode.data.type, targetNode.data.type)
  if (!valid) {
    notify.error(`Cannot connect ${sourceNode.data.type} → ${targetNode.data.type}`)
    return
  }

  store.addEdge({
    id: `${connection.source}-${connection.target}`,
    source: connection.source,
    target: connection.target
  })
}

/* -------------------------------------------------------
   RIGHT CLICK → OPEN NODE CREATION MENU
------------------------------------------------------- */
function onRightClick(event) {
  event.preventDefault()
  const bounds = event.target.getBoundingClientRect()
  menuPos.value = {
    x: event.clientX - bounds.left,
    y: event.clientY - bounds.top
  }
  showMenu.value = true
}

/* -------------------------------------------------------
   CREATE NODE
------------------------------------------------------- */
function createNode(type) {
  const id = 'node_' + Date.now()

  store.addNode({
    id,
    type: 'workflowNode',
    position: { x: menuPos.value.x, y: menuPos.value.y },
    data: { type, params: {}, inputs: [], outputs: [] }
  })

  showMenu.value = false
}

/* -------------------------------------------------------
   NODE CLICK → SELECT + EXECUTION PREVIEW
------------------------------------------------------- */
function onNodeClick(evt) {
  lastClickedNode = evt.node.id
  simulateExecution(evt.node.id)
}

/* -------------------------------------------------------
   EXECUTION PREVIEW (DEMO)
------------------------------------------------------- */
function simulateExecution(nodeId) {
  store.setNodeStatus(nodeId, "running")
  setTimeout(() => {
    const ok = Math.random() > 0.2
    store.setNodeStatus(nodeId, ok ? "success" : "error")
  }, 1500)
}

/* -------------------------------------------------------
   KEYBOARD SHORTCUTS (COPY / PASTE)
------------------------------------------------------- */
function onKeyDown(e) {
  if (e.ctrlKey && e.key === 'c' && lastClickedNode) {
    store.copyNode(lastClickedNode)
    notify.info("Node copied")
  }

  if (e.ctrlKey && e.key === 'v') {
    store.pasteNode({ x: 300, y: 200 })
    notify.success("Node pasted")
  }
}
</script>

<style scoped>
.graph-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.title {
  margin: 0;
  padding: 16px 20px;
  font-size: 24px;
}

.graph-wrapper {
  flex: 1;
  min-height: 0; /* critical for VueFlow layout */
  display: flex;
}

.graph {
  flex: 1;
  background: var(--bg-1);
  border-radius: var(--radius);
}
</style>

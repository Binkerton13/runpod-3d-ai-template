<template>
  <div class="layout">
    <Sidebar />

    <div class="main">
      <TopBar />

      <!-- This must be the ONLY router-view -->
      <div class="content">
        <router-view />
      </div>
    </div>

    <!-- TaskQueue must NOT wrap or sit inside the router-view column -->
    <TaskQueue />
  </div>
</template>

<script setup>
import Sidebar from './Sidebar.vue'
import TopBar from './TopBar.vue'
import TaskQueue from '../components/TaskQueue.vue'
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  background: #1e1e1e;
  color: #ddd;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
</style>

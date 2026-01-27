<template>
  <div class="sidebar">
    <h2 class="title">SpriteForge</h2>

    <nav>
      <router-link to="/motion" class="item" active-class="active">Motion</router-link>
      <router-link to="/sprites" class="item" active-class="active">Sprites</router-link>
      <router-link to="/models" class="item" active-class="active">Models</router-link>
      <router-link to="/projects" class="item" active-class="active">Projects</router-link>
      <router-link to="/workflows/graph" class="item">Workflow Graph</router-link>
    </nav>
  </div>
</template>

<style scoped>
.sidebar {
  width: 220px;
  background: var(--bg-1);
  padding: 20px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
}

.title {
  color: var(--accent);
  margin-bottom: 24px;
  font-size: 20px;
  font-weight: 600;
}

nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item {
  padding: 10px 12px;
  border-radius: var(--radius);
  color: var(--fg-0);
  text-decoration: none;
  transition: background var(--transition), color var(--transition);
}

.item:hover {
  background: var(--bg-2);
}

.active {
  background: var(--accent);
  color: white;
}

</style>

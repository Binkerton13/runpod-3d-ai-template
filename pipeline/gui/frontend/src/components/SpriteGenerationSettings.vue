<template>
  <div class="panel">
    <h2>Settings</h2>
    <label>Resolution</label>
    <input type="number" v-model="model.resolution" />
  </div>
</template>

<script setup>
const { model } = defineProps({
  model: {
    type: Object,
    required: true
  }
})
</script>

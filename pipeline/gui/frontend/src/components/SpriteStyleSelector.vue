<template>
  <div class="panel">
    <h2>Style</h2>

    <select v-model="model.selectedStyle">
      <option disabled value="">Select a style</option>
      <option v-for="s in model.styles" :key="s.id" :value="s.id">
        {{ s.name }}
      </option>
    </select>
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

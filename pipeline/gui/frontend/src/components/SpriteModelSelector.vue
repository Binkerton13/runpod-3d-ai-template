<template>
  <div class="panel">
    <h2>Model</h2>

    <select v-model="model.selectedModel">
      <option disabled value="">Select a model</option>
      <option v-for="m in model.models" :key="m" :value="m">
        {{ m }}
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

<template>
  <button class="upload" @click="open = true">Upload Model</button>

  <FileBrowserModal
    :visible="open"
    @cancel="open = false"
    @choose="onChoose"
  />
</template>

<script setup>
import { ref } from 'vue'
import FileBrowserModal from './FileBrowser/FileBrowserModal.vue'

const open = ref(false)

function onChoose(file) {
  console.log("Selected model file:", file)
  open.value = false
}
</script>

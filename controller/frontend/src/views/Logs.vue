<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <h1>Logs — {{ name }}</h1>
      <div class="actions">
        <button class="btn" :class="{ 'btn-primary': autoScroll }" @click="autoScroll = !autoScroll">
          Auto-scroll: {{ autoScroll ? 'ON' : 'OFF' }}
        </button>
        <button class="btn" @click="clear">Clear</button>
        <button class="btn" @click="reconnect">Reconnect</button>
        <router-link to="/instances" class="btn">Back</router-link>
      </div>
    </div>
    <div
      ref="logContainer"
      style="height: calc(100vh - 120px); background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 16px; overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 13px; line-height: 1.5; white-space: pre-wrap; word-break: break-all"
    >
      <div v-for="(line, i) in lines" :key="i" style="color: #c9d1d9">{{ line }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { wsUrl } from '../api.js'

const props = defineProps({ name: String })
const logContainer = ref(null)
const lines = ref([])
const autoScroll = ref(true)
let ws = null

function scrollToBottom() {
  if (autoScroll.value && logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

function connect() {
  if (ws) ws.close()
  ws = new WebSocket(wsUrl(`/logs/${props.name}`))

  ws.onmessage = (event) => {
    const text = event.data
    text.split('\n').forEach(line => {
      if (line) lines.value.push(line)
    })
    // Keep max 5000 lines
    if (lines.value.length > 5000) {
      lines.value = lines.value.slice(-3000)
    }
    nextTick(scrollToBottom)
  }

  ws.onclose = () => {
    lines.value.push('--- Connection closed ---')
  }
}

function clear() { lines.value = [] }

function reconnect() {
  lines.value = []
  connect()
}

watch(lines, () => nextTick(scrollToBottom), { deep: true })

onMounted(connect)
onUnmounted(() => { if (ws) ws.close() })
</script>

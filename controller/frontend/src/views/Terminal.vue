<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <h1>Terminal — {{ name }}</h1>
      <div class="actions">
        <button class="btn" @click="reconnect">Reconnect</button>
        <router-link to="/instances" class="btn">Back</router-link>
      </div>
    </div>
    <div ref="termContainer" style="height: calc(100vh - 120px); border-radius: 8px; overflow: hidden; border: 1px solid #30363d"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { wsUrl } from '../api.js'
import '@xterm/xterm/css/xterm.css'

const props = defineProps({ name: String })
const termContainer = ref(null)

let term = null
let fitAddon = null
let ws = null

function connect() {
  if (ws) ws.close()

  term = new Terminal({
    theme: {
      background: '#0d1117',
      foreground: '#c9d1d9',
      cursor: '#f0883e',
      selectionBackground: '#264f78',
    },
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
    fontSize: 14,
    cursorBlink: true,
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.open(termContainer.value)
  fitAddon.fit()

  ws = new WebSocket(wsUrl(`/terminal/${props.name}`))
  ws.binaryType = 'arraybuffer'

  ws.onopen = () => {
    term.write('\r\n\x1b[32mConnected to ' + props.name + '\x1b[0m\r\n\r\n')
  }

  ws.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
      term.write(new Uint8Array(event.data))
    } else {
      term.write(event.data)
    }
  }

  ws.onclose = () => {
    term.write('\r\n\x1b[31mDisconnected\x1b[0m\r\n')
  }

  term.onData((data) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(new TextEncoder().encode(data))
    }
  })

  window.addEventListener('resize', () => fitAddon?.fit())
}

function reconnect() {
  if (term) {
    term.dispose()
    term = null
  }
  connect()
}

onMounted(connect)

onUnmounted(() => {
  if (ws) ws.close()
  if (term) term.dispose()
  window.removeEventListener('resize', () => fitAddon?.fit())
})
</script>

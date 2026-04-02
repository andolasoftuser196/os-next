<template>
  <div>
    <h1 style="margin-bottom: 20px">Dashboard</h1>

    <div class="grid grid-4" style="margin-bottom: 24px" v-if="status">
      <div class="card">
        <div class="stat-value">{{ instanceCount }}</div>
        <div class="stat-label">Instances</div>
      </div>
      <div class="card">
        <div class="stat-value">{{ runningCount }}</div>
        <div class="stat-label">Running Containers</div>
      </div>
      <div class="card">
        <div class="stat-value">{{ status.domain || '—' }}</div>
        <div class="stat-label">Domain</div>
      </div>
      <div class="card">
        <div class="stat-value">{{ status.https ? 'HTTPS' : 'HTTP' }}</div>
        <div class="stat-label">Protocol</div>
      </div>
    </div>

    <div class="card">
      <h3>Base Services</h3>
      <table style="width: 100%; border-collapse: collapse">
        <thead>
          <tr style="border-bottom: 1px solid #30363d">
            <th style="text-align: left; padding: 8px; color: #8b949e">Service</th>
            <th style="text-align: left; padding: 8px; color: #8b949e">Status</th>
            <th style="text-align: left; padding: 8px; color: #8b949e">CPU</th>
            <th style="text-align: left; padding: 8px; color: #8b949e">Memory</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(info, name) in status?.services" :key="name" style="border-bottom: 1px solid #21262d">
            <td style="padding: 8px; font-weight: 500">{{ name }}</td>
            <td style="padding: 8px">
              <span class="badge" :class="badgeClass(info.status)">{{ info.status }}</span>
            </td>
            <td style="padding: 8px">{{ serviceStats[name]?.cpu_percent || 0 }}%</td>
            <td style="padding: 8px">{{ serviceStats[name]?.mem_usage_mb || 0 }} MB</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card" v-if="instances.length">
      <h3>Dynamic Instances</h3>
      <table style="width: 100%; border-collapse: collapse">
        <thead>
          <tr style="border-bottom: 1px solid #30363d">
            <th style="text-align: left; padding: 8px; color: #8b949e">Name</th>
            <th style="text-align: left; padding: 8px; color: #8b949e">Type</th>
            <th style="text-align: left; padding: 8px; color: #8b949e">URL</th>
            <th style="text-align: left; padding: 8px; color: #8b949e">Status</th>
            <th style="text-align: left; padding: 8px; color: #8b949e">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="inst in instances" :key="inst.name" style="border-bottom: 1px solid #21262d">
            <td style="padding: 8px; font-weight: 500">{{ inst.name }}</td>
            <td style="padding: 8px">{{ inst.type }}</td>
            <td style="padding: 8px">
              <a :href="inst.url" target="_blank" style="color: #58a6ff">{{ inst.url }}</a>
            </td>
            <td style="padding: 8px">
              <span class="badge" :class="badgeClass(inst.container_status)">{{ inst.container_status }}</span>
            </td>
            <td style="padding: 8px">
              <div class="actions">
                <router-link :to="`/terminal/${inst.name}`" class="btn">Terminal</router-link>
                <router-link :to="`/logs/${inst.name}`" class="btn">Logs</router-link>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api.js'

const status = ref(null)
const instances = ref([])
const serviceStats = ref({})

const instanceCount = computed(() => instances.value.length)
const runningCount = computed(() => {
  const base = Object.values(status.value?.services || {}).filter(s => s.status === 'running').length
  const inst = instances.value.filter(i => i.container_status === 'running').length
  return base + inst
})

function badgeClass(s) {
  if (s === 'running') return 'badge-running'
  if (s === 'exited' || s === 'stopped') return 'badge-stopped'
  return 'badge-error'
}

onMounted(async () => {
  const [s, i] = await Promise.all([api.getStatus(), api.getInstances()])
  status.value = s
  instances.value = i.instances
  // Load stats in background (can be slow)
  api.getServicesStats().then(stats => serviceStats.value = stats).catch(() => {})
})
</script>

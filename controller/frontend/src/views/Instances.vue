<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px">
      <h1>Instances</h1>
      <button class="btn btn-primary" @click="showCreate = !showCreate">+ New Instance</button>
    </div>

    <!-- Create Form -->
    <div class="card" v-if="showCreate">
      <h3>Create Instance</h3>
      <div style="display: flex; gap: 12px; flex-wrap: wrap; align-items: end; margin-top: 12px">
        <div>
          <label style="display: block; font-size: 12px; color: #8b949e; margin-bottom: 4px">Name</label>
          <input v-model="form.name" placeholder="v4-next" style="width: 160px" />
        </div>
        <div>
          <label style="display: block; font-size: 12px; color: #8b949e; margin-bottom: 4px">Type</label>
          <select v-model="form.type" style="width: 140px">
            <option value="v4">V4 (OrangeScrum)</option>
            <option value="selfhosted">Selfhosted</option>
          </select>
        </div>
        <div>
          <label style="display: block; font-size: 12px; color: #8b949e; margin-bottom: 4px">Subdomain</label>
          <input v-model="form.subdomain" placeholder="(same as name)" style="width: 160px" />
        </div>
        <div>
          <label style="display: block; font-size: 12px; color: #8b949e; margin-bottom: 4px">Source Path</label>
          <input v-model="form.source" placeholder="(default)" style="width: 200px" />
        </div>
        <button class="btn btn-primary" @click="create" :disabled="creating">
          {{ creating ? 'Creating...' : 'Create' }}
        </button>
        <button class="btn" @click="showCreate = false">Cancel</button>
      </div>
      <div v-if="createError" style="color: #f85149; margin-top: 8px; font-size: 13px">{{ createError }}</div>
      <div v-if="createSuccess" style="color: #3fb950; margin-top: 8px; font-size: 13px">{{ createSuccess }}</div>
    </div>

    <!-- Instance List -->
    <div class="card" v-for="inst in instances" :key="inst.name">
      <div style="display: flex; justify-content: space-between; align-items: start">
        <div>
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px">
            <h3 style="margin: 0">{{ inst.name }}</h3>
            <span class="badge" :class="badgeClass(inst.container_status)">{{ inst.container_status }}</span>
            <span style="color: #8b949e; font-size: 12px">{{ inst.type }}</span>
          </div>
          <div style="font-size: 13px; color: #8b949e">
            <a :href="inst.url" target="_blank" style="color: #58a6ff">{{ inst.url }}</a>
            &nbsp;&middot;&nbsp; DB: {{ inst.db_name }}
            &nbsp;&middot;&nbsp; Container: {{ inst.container_name }}
          </div>
          <div style="font-size: 12px; color: #6e7681; margin-top: 4px">
            Source: {{ inst.source_path }} &nbsp;&middot;&nbsp; Created: {{ formatDate(inst.created_at) }}
          </div>
        </div>
        <div class="actions">
          <button v-if="inst.container_status !== 'running'" class="btn btn-primary" @click="start(inst.name)">Start</button>
          <button v-if="inst.container_status === 'running'" class="btn btn-warning" @click="stop(inst.name)">Stop</button>
          <button class="btn" @click="dbSetup(inst.name)">DB Setup</button>
          <router-link :to="`/terminal/${inst.name}`" class="btn">Terminal</router-link>
          <router-link :to="`/logs/${inst.name}`" class="btn">Logs</router-link>
          <button class="btn btn-danger" @click="destroy(inst.name)">Destroy</button>
        </div>
      </div>
      <div v-if="messages[inst.name]" style="margin-top: 8px; font-size: 13px; color: #3fb950">{{ messages[inst.name] }}</div>
    </div>

    <div v-if="!instances.length && !showCreate" class="card" style="text-align: center; color: #8b949e; padding: 40px">
      No instances yet. Click <strong>+ New Instance</strong> to create one.
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

const instances = ref([])
const showCreate = ref(false)
const creating = ref(false)
const createError = ref('')
const createSuccess = ref('')
const messages = ref({})

const form = ref({ name: '', type: 'v4', subdomain: '', source: '' })

function badgeClass(s) {
  if (s === 'running') return 'badge-running'
  if (s === 'exited' || s === 'stopped') return 'badge-stopped'
  return 'badge-error'
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleString()
}

async function load() {
  const data = await api.getInstances()
  instances.value = data.instances
}

async function create() {
  creating.value = true
  createError.value = ''
  createSuccess.value = ''
  try {
    const data = {
      name: form.value.name,
      type: form.value.type,
      subdomain: form.value.subdomain || undefined,
      source: form.value.source || undefined,
    }
    const res = await api.createInstance(data)
    createSuccess.value = `${res.message} — ${res.url}`
    form.value = { name: '', type: 'v4', subdomain: '', source: '' }
    await load()
  } catch (e) {
    createError.value = e.message
  }
  creating.value = false
}

async function start(name) {
  await api.startInstance(name)
  messages.value[name] = 'Started'
  await load()
}

async function stop(name) {
  await api.stopInstance(name)
  messages.value[name] = 'Stopped'
  await load()
}

async function destroy(name) {
  if (!confirm(`Destroy instance '${name}'? This will remove the container and config.\n\nDrop database too?`)) return
  const dropDb = confirm('Also drop the PostgreSQL database?')
  await api.destroyInstance(name, dropDb)
  messages.value[name] = 'Destroyed'
  await load()
}

async function dbSetup(name) {
  messages.value[name] = 'Running migrations...'
  try {
    const res = await api.dbSetup(name)
    messages.value[name] = 'DB setup complete'
  } catch (e) {
    messages.value[name] = `DB setup failed: ${e.message}`
  }
}

onMounted(load)
</script>

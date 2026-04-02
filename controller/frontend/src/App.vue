<template>
  <div class="app" v-if="authenticated">
    <nav class="sidebar">
      <div class="logo">
        <h2>Dev</h2>
        <span class="subtitle">Controller</span>
      </div>
      <router-link to="/" class="nav-item">Dashboard</router-link>
      <router-link to="/instances" class="nav-item">Instances</router-link>
      <div style="flex: 1"></div>
      <a class="nav-item" style="cursor: pointer; color: #8b949e" @click="logout">Logout</a>
    </nav>
    <main class="content">
      <router-view />
    </main>
  </div>

  <div v-else class="login-overlay">
    <div class="login-card">
      <h2 style="color: #f0883e; margin-bottom: 4px">Dev Controller</h2>
      <p style="color: #8b949e; margin-bottom: 20px; font-size: 14px">Sign in to manage your instances</p>
      <form @submit.prevent="login">
        <input v-model="loginUser" placeholder="Username" autocomplete="username" style="width: 100%; margin-bottom: 10px" />
        <input v-model="loginPass" type="password" placeholder="Password" autocomplete="current-password" style="width: 100%; margin-bottom: 14px" />
        <button class="btn btn-primary" style="width: 100%; padding: 10px" type="submit" :disabled="loggingIn">
          {{ loggingIn ? 'Signing in...' : 'Sign In' }}
        </button>
        <div v-if="loginError" style="color: #f85149; margin-top: 10px; font-size: 13px">{{ loginError }}</div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api, setAuth, clearAuth, isAuthenticated } from './api.js'

const authenticated = ref(false)
const loginUser = ref('')
const loginPass = ref('')
const loginError = ref('')
const loggingIn = ref(false)

async function login() {
  loggingIn.value = true
  loginError.value = ''
  setAuth(loginUser.value, loginPass.value)
  try {
    await api.getStatus()
    authenticated.value = true
  } catch {
    clearAuth()
    loginError.value = 'Invalid credentials'
  }
  loggingIn.value = false
}

function logout() {
  clearAuth()
  authenticated.value = false
  loginUser.value = ''
  loginPass.value = ''
}

onMounted(() => {
  if (isAuthenticated()) {
    api.getStatus().then(() => authenticated.value = true).catch(() => clearAuth())
  }
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #0f1117;
  color: #e1e4e8;
}

.app {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 220px;
  background: #161b22;
  border-right: 1px solid #30363d;
  padding: 20px 0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.logo {
  padding: 0 20px 20px;
  border-bottom: 1px solid #30363d;
  margin-bottom: 12px;
}

.logo h2 { color: #f0883e; font-size: 18px; }
.logo .subtitle { color: #8b949e; font-size: 12px; }

.nav-item {
  display: block;
  padding: 10px 20px;
  color: #c9d1d9;
  text-decoration: none;
  font-size: 14px;
  transition: background 0.15s;
}

.nav-item:hover { background: #1c2128; }
.nav-item.router-link-exact-active {
  background: #1c2128;
  color: #f0883e;
  border-left: 3px solid #f0883e;
}

.content { flex: 1; padding: 24px; overflow-y: auto; }

.login-overlay {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #0f1117;
}

.login-card {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 12px;
  padding: 32px;
  width: 360px;
}

.card {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
}

.card h3 { margin-bottom: 12px; color: #f0883e; font-size: 16px; }

.btn {
  padding: 6px 14px;
  border: 1px solid #30363d;
  border-radius: 6px;
  background: #21262d;
  color: #c9d1d9;
  cursor: pointer;
  font-size: 13px;
  text-decoration: none;
  transition: background 0.15s;
  display: inline-block;
}

.btn:hover { background: #30363d; }
.btn-primary { background: #238636; border-color: #238636; color: #fff; }
.btn-primary:hover { background: #2ea043; }
.btn-danger { background: #da3633; border-color: #da3633; color: #fff; }
.btn-danger:hover { background: #f85149; }
.btn-warning { background: #9e6a03; border-color: #9e6a03; color: #fff; }

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.badge-running { background: #238636; color: #fff; }
.badge-stopped { background: #6e7681; color: #fff; }
.badge-error { background: #da3633; color: #fff; }

input, select {
  padding: 8px 12px;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 6px;
  color: #c9d1d9;
  font-size: 14px;
}

input:focus, select:focus { outline: none; border-color: #58a6ff; }

.grid { display: grid; gap: 16px; }
.grid-2 { grid-template-columns: 1fr 1fr; }
.grid-3 { grid-template-columns: 1fr 1fr 1fr; }
.grid-4 { grid-template-columns: 1fr 1fr 1fr 1fr; }

.stat-value { font-size: 28px; font-weight: 700; color: #f0883e; }
.stat-label { font-size: 12px; color: #8b949e; margin-top: 4px; }
.actions { display: flex; gap: 6px; flex-wrap: wrap; }
</style>

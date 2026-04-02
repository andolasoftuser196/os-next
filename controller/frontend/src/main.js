import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Dashboard from './views/Dashboard.vue'
import Instances from './views/Instances.vue'
import Terminal from './views/Terminal.vue'
import Logs from './views/Logs.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Dashboard },
    { path: '/instances', component: Instances },
    { path: '/terminal/:name', component: Terminal, props: true },
    { path: '/logs/:name', component: Logs, props: true },
  ],
})

createApp(App).use(router).mount('#app')

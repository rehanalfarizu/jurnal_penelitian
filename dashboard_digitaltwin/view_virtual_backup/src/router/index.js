import { createRouter, createWebHistory } from 'vue-router'

const RouteMarker = {
  name: 'RouteMarker',
  template: '<div aria-hidden="true" style="display:none"></div>'
}

const routes = [
  { path: '/', name: 'root', component: RouteMarker },
  { path: '/dashboard', name: 'dashboard', component: RouteMarker },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

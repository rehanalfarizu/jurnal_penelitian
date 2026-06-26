import { watch } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { useFirebaseAuth } from '../composables/useFirebaseAuth'
import { clearAdminSession, isAdminSessionActive } from '../lib/adminSession'

const RouteMarker = {
  name: 'RouteMarker',
  template: '<div aria-hidden="true" style="display:none"></div>'
}

const routes = [
  { path: '/', name: 'root', component: RouteMarker },
  { path: '/login', name: 'user-login', component: RouteMarker },
  { path: '/admin/login', name: 'admin-login', component: RouteMarker },
  {
    path: '/dashboard',
    name: 'user-dashboard',
    component: RouteMarker,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'admin-dashboard',
    component: RouteMarker,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const { isAuthReady, isAuthenticated, getAdminRoleStatus, signOutUser } = useFirebaseAuth()

const waitForAuthReady = async () => {
  if (isAuthReady.value) return

  await new Promise(resolve => {
    const stopWatch = watch(
      isAuthReady,
      ready => {
        if (!ready) return
        stopWatch()
        resolve()
      },
      { immediate: true }
    )
  })
}

router.beforeEach(async to => {
  await waitForAuthReady()

  const loggedIn = isAuthenticated.value
  const adminSessionActive = isAdminSessionActive()

  if (!adminSessionActive) {
    clearAdminSession()
  }

  // Root route: redirect based on auth state
  if (to.name === 'root') {
    if (!loggedIn) return '/login'
    return adminSessionActive ? '/admin' : '/dashboard'
  }

  // Admin routes: require auth + admin role
  if (to.meta.requiresAdmin) {
    if (!loggedIn || !adminSessionActive) return '/admin/login'

    const adminRole = await getAdminRoleStatus({ forceRefresh: false })
    if (!adminRole.success) {
      clearAdminSession()
      await signOutUser()
      return '/admin/login'
    }
    return true
  }

  // Protected routes: require auth only
  if (to.meta.requiresAuth && !loggedIn) {
    return '/login'
  }

  // User login route: if already logged in → go to dashboard
  if (to.name === 'user-login' && loggedIn) {
    return adminSessionActive ? '/admin' : '/dashboard'
  }

  // Admin login route: if already logged in → go to admin dashboard
  if (to.name === 'admin-login' && loggedIn) {
    if (adminSessionActive) return '/admin'
    // Check if user has admin role, if not → go to user dashboard
    try {
      const adminRole = await getAdminRoleStatus({ forceRefresh: false })
      if (!adminRole.success) {
        return '/dashboard'
      }
    } catch {
      // On error, stay on admin login page
    }
  }

  return true
})

export default router

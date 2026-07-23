import { computed, ref } from 'vue'
import {
  browserLocalPersistence,
  browserSessionPersistence,
  getIdTokenResult,
  getRedirectResult,
  onAuthStateChanged,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
  signInWithRedirect,
  setPersistence,
  signOut
} from 'firebase/auth'
import { auth, googleProvider, isFirebaseConfigured } from '../lib/firebase'

const LOCAL_ADMIN_PROFILE_STORAGE_KEY = 'twinspace_local_admin_profile'

const user = ref(null)
const isAuthReady = ref(false)
const isSigningIn = ref(false)
const authError = ref('')

let authObserverInitialized = false
const credentialDomain = String(import.meta.env.VITE_AUTH_DEFAULT_DOMAIN || '').trim().toLowerCase()
const localAdminEmail = String(import.meta.env.VITE_LOCAL_ADMIN_EMAIL || '').trim().toLowerCase()
const localAdminPassword = String(import.meta.env.VITE_LOCAL_ADMIN_PASSWORD || '').trim()
const localAdminName = String(import.meta.env.VITE_LOCAL_ADMIN_NAME || 'TwinSpace Admin').trim() || 'TwinSpace Admin'
const adminEmailAllowlist = new Set(
  String(import.meta.env.VITE_ADMIN_EMAILS || '')
    .split(',')
    .map(email => email.trim().toLowerCase())
    .filter(Boolean)
)

const readStoredLocalAdminProfile = () => {
  if (typeof window === 'undefined') return null

  try {
    const raw = window.sessionStorage.getItem(LOCAL_ADMIN_PROFILE_STORAGE_KEY)
    if (!raw) return null

    const parsed = JSON.parse(raw)
    const email = String(parsed?.email || '').trim().toLowerCase()
    if (!email) return null

    return {
      uid: String(parsed?.uid || 'local-admin'),
      email,
      displayName: String(parsed?.displayName || localAdminName).trim() || localAdminName,
      isLocalAdmin: true
    }
  } catch {
    return null
  }
}

const persistLocalAdminProfile = profile => {
  if (typeof window === 'undefined') return

  window.sessionStorage.setItem(
    LOCAL_ADMIN_PROFILE_STORAGE_KEY,
    JSON.stringify({
      uid: profile.uid,
      email: profile.email,
      displayName: profile.displayName
    })
  )
}

const clearStoredLocalAdminProfile = () => {
  if (typeof window === 'undefined') return
  window.sessionStorage.removeItem(LOCAL_ADMIN_PROFILE_STORAGE_KEY)
}

const localAdminProfile = ref(readStoredLocalAdminProfile())
if (localAdminProfile.value) {
  user.value = localAdminProfile.value
}

const resolveCredentialEmail = identifier => {
  const normalizedIdentifier = String(identifier || '').trim().toLowerCase()
  if (!normalizedIdentifier) return ''
  if (normalizedIdentifier.includes('@')) return normalizedIdentifier
  if (credentialDomain) return `${normalizedIdentifier}@${credentialDomain}`
  return ''
}

const normalizeRoleValue = value => String(value || '').trim().toLowerCase()

const hasAdminRoleClaims = claims => {
  if (!claims || typeof claims !== 'object') return false

  if (claims.admin === true) return true

  const role = normalizeRoleValue(claims.role)
  if (role === 'admin' || role === 'superadmin') return true

  if (Array.isArray(claims.roles)) {
    const roles = claims.roles.map(normalizeRoleValue)
    if (roles.includes('admin') || roles.includes('superadmin')) return true
  }

  const rolesString = normalizeRoleValue(claims.roles)
  if (rolesString) {
    const roles = rolesString.split(',').map(normalizeRoleValue)
    if (roles.includes('admin') || roles.includes('superadmin')) return true
  }

  return false
}

const mapAuthError = error => {
  if (!error?.code) return 'Login Google gagal. Silakan coba lagi.'

  if (error.code === 'auth/popup-closed-by-user') return ''
  if (error.code === 'auth/popup-blocked') return 'Popup login diblokir browser. Izinkan popup lalu coba lagi.'
  if (error.code === 'auth/cancelled-popup-request') return 'Permintaan popup sebelumnya dibatalkan. Coba login sekali lagi.'
  if (error.code === 'auth/unauthorized-domain') return 'Domain ini belum diizinkan di Firebase Authentication.'
  if (error.code === 'auth/operation-not-allowed') return 'Provider Google belum diaktifkan di Firebase Console.'
  if (error.code === 'auth/configuration-not-found') return 'Konfigurasi Google Sign-In di Firebase belum lengkap.'
  if (error.code === 'auth/auth-domain-config-required') return 'Auth domain Firebase belum benar atau belum dikonfigurasi.'
  if (error.code === 'auth/invalid-api-key') return 'Firebase API key tidak valid.'
  if (error.code === 'auth/app-not-authorized') return 'Aplikasi ini belum diotorisasi untuk Firebase Authentication.'
  if (error.code === 'auth/network-request-failed') return 'Koneksi jaringan bermasalah saat menghubungi Firebase.'
  if (error.code === 'auth/web-storage-unsupported') return 'Browser ini memblokir storage yang dibutuhkan Firebase login.'
  if (error.code === 'auth/invalid-email') return 'Format email tidak valid.'
  if (error.code === 'auth/user-disabled') return 'Akun ini telah dinonaktifkan.'
  if (error.code === 'auth/user-not-found') return 'Akun tidak ditemukan.'
  if (error.code === 'auth/wrong-password') return 'Password yang Anda masukkan salah.'
  if (error.code === 'auth/invalid-credential') return 'Kombinasi email dan password tidak valid.'
  if (error.code === 'auth/too-many-requests') return 'Terlalu banyak percobaan login. Coba lagi beberapa saat.'
  if (error.code === 'auth/missing-password') return 'Password wajib diisi.'

  return `Login Google gagal (${error.code}). Periksa provider Google dan Authorized Domains di Firebase.`
}

const initializeAuthObserver = () => {
  if (authObserverInitialized) return

  if (!isFirebaseConfigured || !auth) {
    user.value = localAdminProfile.value
    isAuthReady.value = true
    authObserverInitialized = true
    return
  }

  getRedirectResult(auth).catch(error => {
    authError.value = mapAuthError(error)
  })

  onAuthStateChanged(
    auth,
    currentUser => {
      user.value = currentUser || localAdminProfile.value
      isAuthReady.value = true
    },
    error => {
      authError.value = mapAuthError(error)
      user.value = localAdminProfile.value
      isAuthReady.value = true
    }
  )

  authObserverInitialized = true
}

export function useFirebaseAuth() {
  initializeAuthObserver()

  const signInWithGoogleRedirect = async () => {
    if (!isFirebaseConfigured || !auth || !googleProvider) {
      authError.value = 'Firebase belum dikonfigurasi. Isi variabel environment terlebih dahulu.'
      return { success: false }
    }

    await signInWithRedirect(auth, googleProvider)
    return { success: true }
  }

  const signInWithGoogle = async () => {
    if (!isFirebaseConfigured || !auth || !googleProvider) {
      authError.value = 'Firebase belum dikonfigurasi. Isi variabel environment terlebih dahulu.'
      return { success: false }
    }

    isSigningIn.value = true
    authError.value = ''

    try {
      await signInWithPopup(auth, googleProvider)
      return { success: true }
    } catch (error) {
      const recoverablePopupErrorCodes = new Set([
        'auth/popup-blocked',
        'auth/web-storage-unsupported',
        'auth/operation-not-supported-in-this-environment'
      ])

      if (recoverablePopupErrorCodes.has(error?.code)) {
        authError.value = 'Popup tidak bisa digunakan. Mengalihkan ke login Google halaman penuh...'
        await signInWithGoogleRedirect()
        return { success: true, redirected: true }
      }

      authError.value = mapAuthError(error)
      return { success: false, error }
    } finally {
      isSigningIn.value = false
    }
  }

  const signInWithEmailPassword = async ({ identifier, password, rememberMe = true }) => {
    if (!isFirebaseConfigured || !auth) {
      authError.value = 'Firebase belum dikonfigurasi. Isi variabel environment terlebih dahulu.'
      return { success: false }
    }

    const normalizedPassword = String(password || '')
    const resolvedEmail = resolveCredentialEmail(identifier)

    if (!String(identifier || '').trim() || !normalizedPassword) {
      authError.value = 'Isi username/email dan password terlebih dahulu.'
      return { success: false }
    }

    if (!resolvedEmail) {
      authError.value = 'Username belum bisa dipetakan ke email. Isi VITE_AUTH_DEFAULT_DOMAIN atau gunakan email lengkap.'
      return { success: false }
    }

    isSigningIn.value = true
    authError.value = ''

    try {
      await setPersistence(auth, rememberMe ? browserLocalPersistence : browserSessionPersistence)
      await signInWithEmailAndPassword(auth, resolvedEmail, normalizedPassword)
      return { success: true }
    } catch (error) {
      authError.value = mapAuthError(error)
      return { success: false, error }
    } finally {
      isSigningIn.value = false
    }
  }

  const requestPasswordReset = async ({ identifier }) => {
    if (!isFirebaseConfigured || !auth) {
      authError.value = 'Firebase belum dikonfigurasi. Isi variabel environment terlebih dahulu.'
      return { success: false }
    }

    const resolvedEmail = resolveCredentialEmail(identifier)

    if (!String(identifier || '').trim()) {
      authError.value = 'Isi username/email terlebih dahulu untuk reset password.'
      return { success: false }
    }

    if (!resolvedEmail) {
      authError.value = 'Username belum bisa dipetakan ke email. Isi VITE_AUTH_DEFAULT_DOMAIN atau gunakan email lengkap.'
      return { success: false }
    }

    try {
      await sendPasswordResetEmail(auth, resolvedEmail)
      authError.value = ''
      return { success: true }
    } catch (error) {
      authError.value = mapAuthError(error)
      return { success: false, error }
    }
  }

  const getAdminRoleStatus = async ({ forceRefresh = false } = {}) => {
    if (localAdminProfile.value) {
      return {
        success: true,
        authorized: true,
        email: localAdminProfile.value.email,
        claims: { admin: true, role: 'admin', local: true },
        source: 'local-env',
        error: ''
      }
    }

    if (!isFirebaseConfigured || !auth || !auth.currentUser) {
      return { success: false, error: 'Sesi login tidak ditemukan.' }
    }

    try {
      const tokenResult = await getIdTokenResult(auth.currentUser, forceRefresh)
      const email = String(auth.currentUser.email || '').trim().toLowerCase()
      const allowlisted = Boolean(email && adminEmailAllowlist.has(email))
      const claimAuthorized = hasAdminRoleClaims(tokenResult.claims)
      const authorized = allowlisted || claimAuthorized

      return {
        success: authorized,
        authorized,
        email,
        claims: tokenResult.claims || {},
        source: claimAuthorized ? 'claims' : allowlisted ? 'allowlist' : 'none',
        error: authorized
          ? ''
          : 'Akun tidak memiliki role admin. Tambahkan custom claim admin=true atau isi VITE_ADMIN_EMAILS.'
      }
    } catch (error) {
      return { success: false, error: mapAuthError(error) }
    }
  }

  const signInAsAdmin = async ({ identifier, password }) => {
    const resolvedEmail = resolveCredentialEmail(identifier) || String(identifier || '').trim().toLowerCase()
    const normalizedPassword = String(password || '')

    if (localAdminEmail && localAdminPassword && resolvedEmail === localAdminEmail) {
      if (normalizedPassword !== localAdminPassword) {
        authError.value = 'Password admin tidak valid.'
        return { success: false, error: authError.value }
      }

      isSigningIn.value = true
      authError.value = ''

      try {
        const profile = {
          uid: 'local-admin',
          email: localAdminEmail,
          displayName: localAdminName,
          isLocalAdmin: true
        }

        localAdminProfile.value = profile
        persistLocalAdminProfile(profile)
        user.value = profile

        return {
          success: true,
          claims: { admin: true, role: 'admin', local: true },
          roleSource: 'local-env',
          email: localAdminEmail
        }
      } finally {
        isSigningIn.value = false
      }
    }

    const signInResult = await signInWithEmailPassword({
      identifier,
      password,
      rememberMe: false
    })

    if (!signInResult.success) {
      return signInResult
    }

    const adminRoleResult = await getAdminRoleStatus({ forceRefresh: true })
    if (adminRoleResult.success) {
      authError.value = ''
      return {
        success: true,
        claims: adminRoleResult.claims,
        roleSource: adminRoleResult.source,
        email: adminRoleResult.email
      }
    }

    await signOutUser()
    authError.value = adminRoleResult.error || 'Akun tidak memiliki role admin.'
    return { success: false, error: authError.value }
  }

  const signOutUser = async () => {
    localAdminProfile.value = null
    clearStoredLocalAdminProfile()

    if (!auth) {
      user.value = null
      return { success: true }
    }

    try {
      if (auth.currentUser) {
        await signOut(auth)
      } else {
        user.value = null
      }
      return { success: true }
    } catch (error) {
      authError.value = 'Gagal keluar dari sesi login.'
      return { success: false, error }
    }
  }

  return {
    user,
    isAuthReady,
    isSigningIn,
    authError,
    isAuthenticated: computed(() => Boolean(user.value)),
    isFirebaseConfigured,
    getAdminRoleStatus,
    requestPasswordReset,
    signInAsAdmin,
    signInWithEmailPassword,
    signInWithGoogle,
    signInWithGoogleRedirect,
    signOutUser
  }
}

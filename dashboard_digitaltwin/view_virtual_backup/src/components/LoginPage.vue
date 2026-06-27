<template>
  <div class="login-page" :class="{ dark: isDarkMode }">
    <div class="backdrop-grid"></div>

    <header class="topbar">
      <div class="brand">
        <img src="/logo.png" alt="TwinSpace" class="brand-logo" />
        <div class="brand-text">
          <strong>TwinSpace</strong>
          <span>Digital Twin Operations</span>
        </div>
      </div>

      <button class="theme-btn" type="button" :title="themeLabel" :aria-label="themeLabel" @click="emit('toggle-theme')">
        <svg
          v-if="isDarkMode"
          class="theme-svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.9"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="4.2" />
          <path d="M12 2.4v2.2" />
          <path d="M12 19.4v2.2" />
          <path d="M4.8 4.8l1.6 1.6" />
          <path d="M17.6 17.6l1.6 1.6" />
          <path d="M2.4 12h2.2" />
          <path d="M19.4 12h2.2" />
          <path d="M4.8 19.2l1.6-1.6" />
          <path d="M17.6 6.4l1.6-1.6" />
        </svg>
        <svg
          v-else
          class="theme-svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.9"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M21.4 14.7A9.2 9.2 0 1 1 9.3 2.6a7.6 7.6 0 1 0 12.1 12.1z" />
        </svg>
        <span class="sr-only">{{ themeLabel }}</span>
      </button>
    </header>

    <main class="layout">
      <section class="intro-panel">
        <p class="eyebrow">Building Intelligence Platform</p>
        <h1 class="headline">Kontrol performa gedung dari satu dashboard yang jelas dan real-time.</h1>
        <p class="intro-copy">
          TwinSpace membantu tim operasional memantau kondisi sensor, konsumsi energi, dan insight prediktif
          dalam satu tampilan yang terstruktur.
        </p>

        <div class="status-strip">
          <div class="status-chip">
            <span class="chip-dot chip-online"></span>
            Telemetry aktif
          </div>
          <div class="status-chip">
            <span class="chip-dot chip-ai"></span>
            Insight prediktif
          </div>
        </div>

        <ul class="highlights">
          <li class="highlight-item">
            <span class="highlight-index">01</span>
            <div>
              <strong>Monitoring multisensor terpusat</strong>
              <p>Suhu, kelembaban, daya, arus, tegangan, dan people count dalam satu alur pemantauan.</p>
            </div>
          </li>
          <li class="highlight-item">
            <span class="highlight-index">02</span>
            <div>
              <strong>Respons operasional lebih cepat</strong>
              <p>Deteksi anomali lebih dini dengan pembacaan data yang konsisten dan mudah ditindaklanjuti.</p>
            </div>
          </li>
          <li class="highlight-item">
            <span class="highlight-index">03</span>
            <div>
              <strong>Akses aman untuk user dan admin</strong>
              <p>Masuk dengan Google untuk user, serta mode admin terpisah untuk kontrol internal.</p>
            </div>
          </li>
        </ul>
      </section>

      <section class="auth-panel">
        <div class="auth-card">
          <div class="auth-header">
            <h2>{{ loginTitle }}</h2>
            <p>{{ loginSubtitle }}</p>
          </div>

          <div v-if="!isModeLocked" class="mode-switch" role="tablist" aria-label="Pilih mode login">
            <button
              class="mode-btn"
              :class="{ active: !activeIsAdminMode }"
              type="button"
              role="tab"
              title="Mode User"
              aria-label="Mode User"
              :aria-selected="!activeIsAdminMode"
              @click="setMode(false)"
            >
              <svg
                class="mode-svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.9"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <circle cx="12" cy="8" r="3.3" />
                <path d="M5.6 19.2c1.3-2.8 3.5-4.2 6.4-4.2s5.1 1.4 6.4 4.2" />
              </svg>
              <span class="sr-only">User</span>
            </button>
            <button
              class="mode-btn"
              :class="{ active: activeIsAdminMode }"
              type="button"
              role="tab"
              title="Mode Admin"
              aria-label="Mode Admin"
              :aria-selected="activeIsAdminMode"
              @click="setMode(true)"
            >
              <svg
                class="mode-svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.9"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path d="M12 3.2l6.4 2.6v4.8c0 4.2-2.8 7.3-6.4 8.8-3.6-1.5-6.4-4.6-6.4-8.8V5.8L12 3.2z" />
                <path d="M9.4 12.2l1.7 1.7 3.5-3.5" />
              </svg>
              <span class="sr-only">Admin</span>
            </button>
          </div>

          <div v-if="!activeIsAdminMode" class="auth-body user-body">
            <form class="user-form" @submit.prevent="handleUserCredentialLogin">
              <label for="user-identifier" class="admin-label">Username / Email</label>
              <input
                id="user-identifier"
                v-model="userIdentifier"
                class="admin-input user-input"
                type="text"
                placeholder="contoh: operator@company.com"
                autocomplete="username"
                required
              />

              <label for="user-password" class="admin-label">Password</label>
              <div class="pin-input-wrap">
                <input
                  id="user-password"
                  v-model="userPassword"
                  class="admin-input"
                  :type="showUserPassword ? 'text' : 'password'"
                  placeholder="Masukkan password"
                  autocomplete="current-password"
                  required
                />
                <button
                  class="pin-toggle"
                  type="button"
                  :aria-label="showUserPassword ? 'Sembunyikan password' : 'Tampilkan password'"
                  :title="showUserPassword ? 'Sembunyikan password' : 'Tampilkan password'"
                  @click="toggleUserPasswordVisibility"
                >
                  <svg
                    v-if="showUserPassword"
                    class="icon-eye"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.9"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M2.5 12s3.3-5.6 9.5-5.6S21.5 12 21.5 12s-3.3 5.6-9.5 5.6S2.5 12 2.5 12z" />
                    <circle cx="12" cy="12" r="2.9" />
                    <path d="M4 20L20 4" />
                  </svg>
                  <svg
                    v-else
                    class="icon-eye"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.9"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M2.5 12s3.3-5.6 9.5-5.6S21.5 12 21.5 12s-3.3 5.6-9.5 5.6S2.5 12 2.5 12z" />
                    <circle cx="12" cy="12" r="2.9" />
                  </svg>
                </button>
              </div>

              <div class="user-tools">
                <label class="remember-wrap">
                  <input v-model="rememberMe" type="checkbox" />
                  <span>Ingat saya</span>
                </label>
                <button class="forgot-btn" type="button" @click="handleForgotPassword">
                  Lupa password?
                </button>
              </div>

              <button
                class="user-btn-login"
                type="submit"
                :disabled="!isAuthReady || isSigningIn || !isFirebaseConfigured"
              >
                {{ credentialButtonLabel }}
              </button>
              <p v-if="userFormError" class="pin-error" aria-live="polite">{{ userFormError }}</p>
              <p v-if="passwordResetInfo" class="reset-info" aria-live="polite">{{ passwordResetInfo }}</p>
            </form>

            <div class="auth-divider"><span>atau</span></div>

            <button
              class="google-btn"
              type="button"
              :disabled="!isAuthReady || isSigningIn || !isFirebaseConfigured"
              @click="emit('login-google')"
            >
              <span class="google-icon-wrap" aria-hidden="true">
                <svg viewBox="0 0 24 24" class="google-svg">
                  <path
                    fill="#EA4335"
                    d="M5.27 9.76A7.08 7.08 0 0 1 12 5.48c1.78 0 3.37.61 4.63 1.8l3.47-3.37C17.95 1.95 15.24.76 12 .76A11.24 11.24 0 0 0 1.24 7.47l4.03 2.29Z"
                  />
                  <path
                    fill="#34A853"
                    d="M16.04 18.01A6.72 6.72 0 0 1 12 19.28 7.08 7.08 0 0 0 5.27 15l-4.03 2.29A11.24 11.24 0 0 0 12 24a10.7 10.7 0 0 0 7.38-2.73l-3.34-3.26Z"
                  />
                  <path
                    fill="#4285F4"
                    d="M19.38 21.27C21.72 19.16 23.24 15.93 23.24 12c0-.67-.08-1.35-.22-2H12v4.26h6.32a5.6 5.6 0 0 1-2.28 3.48l3.34 3.26.01.27Z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.27 15a7 7 0 0 1 0-5.24L1.24 7.47A11.18 11.18 0 0 0 .76 12c0 1.83.44 3.55 1.2 5.09l3.31-2.09Z"
                  />
                </svg>
              </span>

              <span>{{ buttonLabel }}</span>
              <span v-if="isSigningIn" class="btn-spinner" aria-hidden="true"></span>
            </button>

           
          </div>

          <form v-else class="auth-body admin-form" @submit.prevent="handleAdminLogin">
            <label for="admin-identifier" class="admin-label">Email Admin</label>
            <input
              id="admin-identifier"
              v-model="adminIdentifier"
              class="admin-input"
              type="email"
              placeholder="admin@company.com"
              autocomplete="username"
              required
            />

            <label for="admin-password" class="admin-label">Password Admin</label>
            <div class="pin-input-wrap">
              <input
                id="admin-password"
                v-model="adminPassword"
                class="admin-input"
                :type="showAdminPassword ? 'text' : 'password'"
                placeholder="Masukkan password admin"
                autocomplete="current-password"
                required
              />
              <button
                class="pin-toggle"
                type="button"
                :aria-label="showAdminPassword ? 'Sembunyikan password admin' : 'Tampilkan password admin'"
                :title="showAdminPassword ? 'Sembunyikan password admin' : 'Tampilkan password admin'"
                @click="toggleAdminPasswordVisibility"
              >
                <svg
                  v-if="showAdminPassword"
                  class="icon-eye"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.9"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M2.5 12s3.3-5.6 9.5-5.6S21.5 12 21.5 12s-3.3 5.6-9.5 5.6S2.5 12 2.5 12z" />
                  <circle cx="12" cy="12" r="2.9" />
                  <path d="M4 20L20 4" />
                </svg>
                <svg
                  v-else
                  class="icon-eye"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.9"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M2.5 12s3.3-5.6 9.5-5.6S21.5 12 21.5 12s-3.3 5.6-9.5 5.6S2.5 12 2.5 12z" />
                  <circle cx="12" cy="12" r="2.9" />
                </svg>
              </button>
            </div>

            <button class="admin-btn-login" type="submit">Masuk sebagai Admin</button>
            <p v-if="adminError" class="pin-error" aria-live="polite">{{ adminError }}</p>
            <p class="helper-text">Mode admin hanya untuk konfigurasi dan kontrol operasional internal.</p>
          </form>

          <p v-if="mode === 'user'" class="alt-login-link">
            Butuh akses admin?
            <RouterLink class="alt-login-anchor" to="/admin/login">Buka login admin</RouterLink>
          </p>

          <p v-if="mode === 'admin'" class="alt-login-link">
            Kembali ke akses operator:
            <RouterLink class="alt-login-anchor" to="/login">Buka login user</RouterLink>
          </p>

          <div v-if="!isFirebaseConfigured" class="notice warning" aria-live="polite">
            Konfigurasi VITE_FIREBASE_* di file <code>.env</code> belum lengkap.
          </div>
          <div v-else-if="authError" class="notice error" aria-live="polite">
            {{ authError }}
          </div>
        </div>

        <p class="footer-copy">Digital Twin Dashboard &copy; {{ releaseYear }}</p>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  isDarkMode: { type: Boolean, default: false },
  isAuthReady: { type: Boolean, default: false },
  isSigningIn: { type: Boolean, default: false },
  authError: { type: String, default: '' },
  isFirebaseConfigured: { type: Boolean, default: false },
  mode: {
    type: String,
    default: 'both',
    validator: value => ['both', 'user', 'admin'].includes(value)
  }
})

const emit = defineEmits(['login-google', 'login-credentials', 'forgot-password', 'login-admin', 'toggle-theme'])

const isAdminMode = ref(false)
const userIdentifier = ref('')
const userPassword = ref('')
const rememberMe = ref(true)
const userFormError = ref('')
const passwordResetInfo = ref('')
const showUserPassword = ref(false)
const adminIdentifier = ref('')
const adminPassword = ref('')
const adminError = ref('')
const showAdminPassword = ref(false)
const releaseYear = new Date().getFullYear()

const isModeLocked = computed(() => props.mode === 'user' || props.mode === 'admin')

const activeIsAdminMode = computed(() => {
  if (props.mode === 'admin') return true
  if (props.mode === 'user') return false
  return isAdminMode.value
})

const loginTitle = computed(() => {
  if (props.mode === 'admin') return 'Login Admin'
  if (props.mode === 'user') return 'Login User'
  return 'Masuk ke Dashboard'
})

const loginSubtitle = computed(() => {
  if (props.mode === 'admin') return 'Halaman ini hanya untuk akun admin resmi.'
  if (props.mode === 'user') return 'Masuk sebagai operator atau user dashboard.'
  return 'Pilih mode akses sesuai peran Anda.'
})

const resetLoginForms = () => {
  userIdentifier.value = ''
  userPassword.value = ''
  rememberMe.value = true
  userFormError.value = ''
  passwordResetInfo.value = ''
  showUserPassword.value = false
  adminError.value = ''
  adminIdentifier.value = ''
  adminPassword.value = ''
  showAdminPassword.value = false
}

const setMode = (nextIsAdminMode) => {
  if (isModeLocked.value) return

  isAdminMode.value = nextIsAdminMode
  resetLoginForms()
}

watch(
  () => props.mode,
  nextMode => {
    isAdminMode.value = nextMode === 'admin'
    resetLoginForms()
  },
  { immediate: true }
)

const toggleUserPasswordVisibility = () => {
  showUserPassword.value = !showUserPassword.value
}

const handleUserCredentialLogin = () => {
  userFormError.value = ''
  passwordResetInfo.value = ''

  const identifier = userIdentifier.value.trim()
  const password = userPassword.value

  if (!identifier || !password) {
    userFormError.value = 'Isi username/email dan password terlebih dahulu.'
    return
  }

  emit('login-credentials', { identifier, password, rememberMe: rememberMe.value })
}

const handleForgotPassword = () => {
  userFormError.value = ''
  passwordResetInfo.value = ''

  const identifier = userIdentifier.value.trim()
  if (!identifier) {
    userFormError.value = 'Isi username/email terlebih dahulu untuk reset password.'
    return
  }

  emit('forgot-password', { identifier })
  passwordResetInfo.value = 'Jika akun terdaftar, tautan reset password akan dikirim ke email Anda.'
}

const toggleAdminPasswordVisibility = () => {
  showAdminPassword.value = !showAdminPassword.value
}

const handleAdminLogin = () => {
  adminError.value = ''

  const identifier = adminIdentifier.value.trim()
  const password = adminPassword.value

  if (!identifier || !password) {
    adminError.value = 'Isi email dan password admin terlebih dahulu.'
    return
  }

  emit('login-admin', { identifier, password })
}

const buttonLabel = computed(() => {
  if (!props.isAuthReady) return 'Menyiapkan autentikasi...'
  if (!props.isFirebaseConfigured) return 'Firebase belum siap'
  if (props.isSigningIn) return 'Memproses login...'
  return 'Lanjutkan dengan Google'
})

const credentialButtonLabel = computed(() => {
  if (!props.isAuthReady) return 'Menyiapkan autentikasi...'
  if (!props.isFirebaseConfigured) return 'Firebase belum siap'
  if (props.isSigningIn) return 'Memproses login...'
  return 'Masuk dengan Username/Email'
})

const themeLabel = computed(() => (props.isDarkMode ? 'Mode Terang' : 'Mode Gelap'))
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Sora:wght@500;600;700;800&display=swap');

.login-page {
  --surface-card: rgba(255, 255, 255, 0.83);
  --surface-panel: rgba(255, 255, 255, 0.66);
  --surface-chip: rgba(255, 255, 255, 0.92);
  --text-strong: #0f172a;
  --text-soft: #475569;
  --text-muted: #6b7280;
  --line: rgba(15, 23, 42, 0.14);
  --accent: #0ea5a4;
  --accent-deep: #0284c7;
  --accent-soft: rgba(14, 165, 164, 0.14);
  --error-bg: rgba(239, 68, 68, 0.1);
  --error-text: #b91c1c;
  --warn-bg: rgba(245, 158, 11, 0.12);
  --warn-text: #92400e;

  position: relative;
  min-height: 100vh;
  padding: 28px 32px 40px;
  overflow: hidden;
  color: var(--text-strong);
  background:
    radial-gradient(circle at 8% 10%, rgba(14, 165, 164, 0.2), transparent 34%),
    radial-gradient(circle at 94% 12%, rgba(2, 132, 199, 0.2), transparent 38%),
    radial-gradient(circle at 50% 90%, rgba(6, 182, 212, 0.12), transparent 42%),
    linear-gradient(130deg, #f8fcff 0%, #edf5ff 44%, #f4fff8 100%);
}

.login-page.dark {
  --surface-card: rgba(10, 18, 31, 0.85);
  --surface-panel: rgba(6, 13, 24, 0.62);
  --surface-chip: rgba(15, 23, 42, 0.88);
  --text-strong: #e2e8f0;
  --text-soft: #cbd5e1;
  --text-muted: #94a3b8;
  --line: rgba(148, 163, 184, 0.26);
  --accent: #14b8a6;
  --accent-deep: #0ea5e9;
  --accent-soft: rgba(20, 184, 166, 0.2);
  --error-bg: rgba(248, 113, 113, 0.13);
  --error-text: #fecaca;
  --warn-bg: rgba(251, 191, 36, 0.16);
  --warn-text: #fde68a;

  background:
    radial-gradient(circle at 10% 12%, rgba(20, 184, 166, 0.24), transparent 36%),
    radial-gradient(circle at 92% 10%, rgba(14, 165, 233, 0.18), transparent 38%),
    radial-gradient(circle at 50% 94%, rgba(20, 184, 166, 0.12), transparent 40%),
    linear-gradient(130deg, #020817 0%, #061324 46%, #03131e 100%);
}

.backdrop-grid {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.35;
  background-image:
    linear-gradient(to right, rgba(148, 163, 184, 0.16) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(148, 163, 184, 0.16) 1px, transparent 1px);
  background-size: 32px 32px;
  mask-image: radial-gradient(circle at center, black 32%, transparent 90%);
}

.topbar {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-logo {
  width: 46px;
  height: 46px;
  border-radius: 13px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 8px 24px rgba(2, 132, 199, 0.18);
  padding: 6px;
  object-fit: contain;
}

.dark .brand-logo {
  background: rgba(15, 23, 42, 0.88);
  box-shadow: 0 10px 26px rgba(0, 0, 0, 0.4);
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.brand-text strong {
  font-family: 'Sora', sans-serif;
  font-weight: 700;
  font-size: 1rem;
  line-height: 1.2;
}

.brand-text span {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.82rem;
  color: var(--text-muted);
}

.theme-btn {
  width: 42px;
  height: 42px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface-chip);
  color: var(--text-strong);
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.84rem;
  font-weight: 600;
  padding: 0;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
}

.theme-svg {
  width: 18px;
  height: 18px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.theme-btn:hover {
  transform: translateY(-1px);
  border-color: var(--accent-deep);
  box-shadow: 0 8px 20px rgba(2, 132, 199, 0.18);
}

.layout {
  position: relative;
  z-index: 2;
  min-height: calc(100vh - 132px);
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(360px, 470px);
  gap: 34px;
  align-items: stretch;
}

.intro-panel,
.auth-card {
  border: 1px solid var(--line);
  background: var(--surface-panel);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-radius: 26px;
}

.intro-panel {
  padding: 38px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  animation: enterUp 0.65s ease both;
}

.eyebrow {
  margin: 0;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent-deep);
}

.headline {
  margin: 0;
  font-family: 'Sora', sans-serif;
  font-size: clamp(1.8rem, 3.1vw, 2.7rem);
  line-height: 1.22;
  letter-spacing: -0.03em;
}

.intro-copy {
  margin: 0;
  max-width: 64ch;
  font-family: 'IBM Plex Sans', sans-serif;
  color: var(--text-soft);
  line-height: 1.7;
}

.status-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface-chip);
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-soft);
  padding: 8px 12px;
}

.chip-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.chip-online {
  background: #10b981;
  box-shadow: 0 0 0 6px rgba(16, 185, 129, 0.15);
}

.chip-ai {
  background: #0284c7;
  box-shadow: 0 0 0 6px rgba(2, 132, 199, 0.16);
}

.highlights {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.highlight-item {
  display: flex;
  gap: 14px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--surface-chip);
  animation: enterUp 0.6s ease both;
}

.highlight-item:nth-child(2) {
  animation-delay: 0.08s;
}

.highlight-item:nth-child(3) {
  animation-delay: 0.16s;
}

.highlight-index {
  font-family: 'Sora', sans-serif;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--accent-deep);
  border: 1px solid rgba(2, 132, 199, 0.32);
  border-radius: 10px;
  min-width: 36px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-soft);
}

.highlight-item strong {
  font-family: 'Sora', sans-serif;
  font-size: 0.95rem;
}

.highlight-item p {
  margin: 4px 0 0;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.86rem;
  line-height: 1.55;
  color: var(--text-soft);
}

.auth-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.auth-card {
  background: var(--surface-card);
  padding: 30px;
  box-shadow:
    0 18px 45px rgba(15, 23, 42, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.45);
  animation: enterUp 0.78s ease both;
}

.dark .auth-card {
  box-shadow:
    0 22px 55px rgba(0, 0, 0, 0.42),
    inset 0 1px 0 rgba(148, 163, 184, 0.12);
}

.auth-header h2 {
  margin: 0;
  font-family: 'Sora', sans-serif;
  font-size: 1.45rem;
  letter-spacing: -0.02em;
}

.auth-header p {
  margin: 8px 0 0;
  font-family: 'IBM Plex Sans', sans-serif;
  color: var(--text-soft);
}

.mode-switch {
  margin-top: 22px;
  padding: 5px;
  border-radius: 13px;
  border: 1px solid var(--line);
  background: rgba(148, 163, 184, 0.12);
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.mode-btn {
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--text-muted);
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.9rem;
  font-weight: 700;
  padding: 10px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.mode-svg {
  width: 18px;
  height: 18px;
}

.mode-btn.active {
  background: var(--surface-chip);
  color: var(--accent-deep);
  box-shadow: 0 6px 16px rgba(2, 132, 199, 0.18);
}

.mode-btn:hover {
  transform: translateY(-1px);
}

.auth-body {
  margin-top: 18px;
}

.user-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-input {
  padding-right: 14px;
}

.user-btn-login {
  width: 100%;
  border: none;
  border-radius: 14px;
  padding: 13px 15px;
  color: #e6f8ff;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  background: linear-gradient(135deg, #0f766e 0%, #0369a1 100%);
  box-shadow: 0 10px 20px rgba(2, 132, 199, 0.24);
  transition: transform 0.25s ease, box-shadow 0.25s ease, opacity 0.25s ease;
}

.user-btn-login:hover:enabled {
  transform: translateY(-2px);
  box-shadow: 0 14px 28px rgba(2, 132, 199, 0.32);
}

.user-btn-login:disabled {
  opacity: 0.58;
  cursor: not-allowed;
}

.auth-divider {
  margin: 14px 0 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.auth-divider::before,
.auth-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--line);
}

.auth-divider span {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.google-btn,
.admin-btn-login {
  width: 100%;
  border: none;
  border-radius: 14px;
  padding: 13px 15px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
}

.google-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #0f172a;
  background: linear-gradient(130deg, #ffffff 0%, #eef2ff 100%);
  border: 1px solid rgba(148, 163, 184, 0.48);
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}

.dark .google-btn {
  color: #e2e8f0;
  background: linear-gradient(130deg, #0b1627 0%, #1d2d45 100%);
  border-color: rgba(148, 163, 184, 0.4);
}

.google-btn:enabled:hover {
  transform: translateY(-2px);
  border-color: rgba(2, 132, 199, 0.52);
  box-shadow: 0 12px 24px rgba(2, 132, 199, 0.2);
}

.google-btn:disabled {
  opacity: 0.58;
  cursor: not-allowed;
}

.google-icon-wrap {
  width: 20px;
  height: 20px;
  display: inline-flex;
}

.google-svg {
  width: 100%;
  height: 100%;
}

.admin-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.admin-label {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.pin-input-wrap {
  position: relative;
}

.admin-input {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--text-strong);
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.95rem;
  font-weight: 600;
  padding: 12px 52px 12px 14px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.dark .admin-input {
  background: rgba(15, 23, 42, 0.9);
}

.admin-input:focus {
  outline: none;
  border-color: rgba(2, 132, 199, 0.6);
  box-shadow: 0 0 0 4px rgba(2, 132, 199, 0.15);
}

.pin-toggle {
  position: absolute;
  top: 50%;
  right: 8px;
  transform: translateY(-50%);
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--surface-chip);
  color: var(--text-soft);
  width: 34px;
  height: 34px;
  padding: 0;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s ease, background-color 0.2s ease, color 0.2s ease;
}

.pin-toggle:hover {
  border-color: rgba(2, 132, 199, 0.5);
  color: var(--accent-deep);
}

.icon-eye {
  width: 18px;
  height: 18px;
}

.user-tools {
  margin-top: -2px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.remember-wrap {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.83rem;
  color: var(--text-soft);
  cursor: pointer;
}

.remember-wrap input {
  width: 16px;
  height: 16px;
  accent-color: #0284c7;
}

.forgot-btn {
  border: none;
  background: transparent;
  color: var(--accent-deep);
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.83rem;
  font-weight: 700;
  cursor: pointer;
  padding: 2px 0;
}

.forgot-btn:hover {
  text-decoration: underline;
}

.admin-btn-login {
  color: #e6f8ff;
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-deep) 100%);
  box-shadow: 0 10px 20px rgba(2, 132, 199, 0.24);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.admin-btn-login:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 28px rgba(2, 132, 199, 0.32);
}

.pin-error {
  margin: 0;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.84rem;
  font-weight: 600;
  color: #ef4444;
}

.reset-info {
  margin: 0;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.82rem;
  font-weight: 600;
  color: #0f766e;
}

.dark .reset-info {
  color: #5eead4;
}

.helper-text {
  margin: 10px 0 0;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.82rem;
  color: var(--text-muted);
  line-height: 1.55;
}

.alt-login-link {
  margin: 12px 0 0;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.82rem;
  color: var(--text-soft);
}

.alt-login-anchor {
  color: var(--accent-deep);
  font-weight: 700;
  text-decoration: none;
}

.alt-login-anchor:hover {
  text-decoration: underline;
}

.notice {
  margin-top: 14px;
  border-radius: 12px;
  border: 1px solid transparent;
  padding: 11px 13px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.84rem;
  line-height: 1.5;
}

.notice code {
  background: rgba(148, 163, 184, 0.2);
  border-radius: 7px;
  padding: 2px 5px;
}

.notice.warning {
  background: var(--warn-bg);
  border-color: rgba(245, 158, 11, 0.34);
  color: var(--warn-text);
}

.notice.error {
  background: var(--error-bg);
  border-color: rgba(239, 68, 68, 0.34);
  color: var(--error-text);
}

.btn-spinner {
  width: 15px;
  height: 15px;
  border: 2px solid rgba(2, 132, 199, 0.28);
  border-top-color: #0284c7;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.footer-copy {
  margin: 14px 2px 0;
  text-align: right;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.76rem;
  color: var(--text-muted);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes enterUp {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1100px) {
  .layout {
    grid-template-columns: 1fr;
    gap: 22px;
  }

  .footer-copy {
    text-align: left;
  }
}

@media (max-width: 640px) {
  .login-page {
    padding: 18px 16px 28px;
  }

  .topbar {
    margin-bottom: 16px;
  }

  .brand-logo {
    width: 42px;
    height: 42px;
  }

  .intro-panel,
  .auth-card {
    border-radius: 18px;
  }

  .intro-panel {
    padding: 24px 18px;
    gap: 16px;
  }

  .auth-card {
    padding: 22px 18px;
  }

  .headline {
    font-size: clamp(1.45rem, 7vw, 1.85rem);
  }

  .theme-btn {
    padding: 8px 11px;
    font-size: 0.78rem;
  }
}
</style>

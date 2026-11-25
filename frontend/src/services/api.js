// One axios instance. The JWT token (saved at login) is attached to every request.
import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// If the token expired, clear it and go to login.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const requestUrl = error.config?.url || ''
    if (error.response?.status === 401 && !requestUrl.includes('/auth/login')) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

// Turn any axios error into a readable message for toasts.
export function errorMessage(error) {
  const detail = error.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join('; ')
  if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
    return `Cannot reach the API at ${api.defaults.baseURL}. Start the backend server and try again.`
  }
  if (error.code === 'ECONNABORTED') return 'The request timed out. Please try again.'
  return detail || error.message || 'Something went wrong'
}

// Download a protected file (resume / export) with the auth header, then save it in the browser.
export async function downloadFile(url, filename) {
  const response = await api.get(url, { responseType: 'blob' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(response.data)
  link.download = filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(link.href), 0)
}

export default api

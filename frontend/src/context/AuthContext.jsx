import { createContext, useContext, useState } from 'react'
import api from '../services/api'

const AuthContext = createContext(null)

// The three roles and the page each one lands on after login.
export const HOME_BY_ROLE = { admin: '/admin', candidate: '/candidate', interviewer: '/interviewer' }

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user')
    return saved ? JSON.parse(saved) : null
  })

  function saveSession(data) {
    localStorage.setItem('token', data.access_token)
    const session = { role: data.role, full_name: data.full_name }
    localStorage.setItem('user', JSON.stringify(session))
    setUser(session)
    return session
  }

  async function login(email, password) {
    const { data } = await api.post('/api/auth/login', { email, password })
    return saveSession(data)
  }

  async function register(full_name, email, password) {
    const { data } = await api.post('/api/auth/register', { full_name, email, password })
    return saveSession(data)
  }

  function logout() {
    localStorage.clear()
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, login, register, logout }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)

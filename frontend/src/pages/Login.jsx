import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth, HOME_BY_ROLE } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { errorMessage } from '../services/api'
import { Field } from '../components/ui'
import AuthLayout from '../components/AuthLayout'

export default function Login() {
  const { login } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setBusy(true)
    try {
      const session = await login(form.email, form.password)
      navigate(HOME_BY_ROLE[session.role])
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout title="Welcome back" description="Sign in to continue to your recruitment workspace.">
      <form onSubmit={handleSubmit}>
        <Field label="Email"><input className="input" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
        <Field label="Password"><input className="input" type="password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
        <div className="-mt-1 mb-4 text-right text-sm">
          <Link className="font-semibold text-brand-700 hover:text-brand-800" to="/forgot-password">Forgot password?</Link>
        </div>
        <button className="btn-primary mt-2 w-full" disabled={busy}>{busy ? 'Signing in...' : 'Sign in'}</button>
        <p className="mt-5 text-center text-sm text-slate-500">New candidate? <Link className="font-semibold text-brand-700 hover:text-brand-800" to="/register">Create an account</Link></p>
      </form>
    </AuthLayout>
  )
}

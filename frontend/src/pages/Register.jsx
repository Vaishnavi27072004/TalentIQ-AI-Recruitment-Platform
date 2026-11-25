import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth, HOME_BY_ROLE } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { errorMessage } from '../services/api'
import { Field } from '../components/ui'
import AuthLayout from '../components/AuthLayout'

export default function Register() {
  const { register } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState({ full_name: '', email: '', password: '' })
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setBusy(true)
    try {
      const session = await register(form.full_name, form.email, form.password)
      navigate(HOME_BY_ROLE[session.role])
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout title="Create your account" description="Set up your candidate profile and start exploring opportunities.">
      <form onSubmit={handleSubmit}>
        <Field label="Full name"><input className="input" required minLength={2} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
        <Field label="Email"><input className="input" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
        <Field label="Password (min 8 characters)"><input className="input" type="password" required minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
        <button className="btn-primary mt-2 w-full" disabled={busy}>{busy ? 'Creating...' : 'Create account'}</button>
        <p className="mt-5 text-center text-sm text-slate-500">Already registered? <Link className="font-semibold text-brand-700 hover:text-brand-800" to="/login">Sign in</Link></p>
      </form>
    </AuthLayout>
  )
}

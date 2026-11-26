import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useToast } from '../context/ToastContext'
import { errorMessage } from '../services/api'
import { Field } from '../components/ui'
import AuthLayout from '../components/AuthLayout'
import api from '../services/api'

export default function ForgotPassword() {
  const toast = useToast()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [token, setToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [requested, setRequested] = useState(false)
  const [busy, setBusy] = useState(false)

  async function requestReset(event) {
    event.preventDefault()
    setBusy(true)
    try {
      const { data } = await api.post('/api/auth/password-reset/request', { email })
      setRequested(true)
      toast.success(data.message)
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  async function confirmReset(event) {
    event.preventDefault()
    setBusy(true)
    try {
      const { data } = await api.post('/api/auth/password-reset/confirm', {
        token,
        new_password: newPassword,
      })
      toast.success(data.message)
      navigate('/login')
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout title="Reset your password" description="Request a reset token, then use it to choose a new password.">
      {!requested ? (
        <form onSubmit={requestReset}>
          <Field label="Email">
            <input className="input" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
          </Field>
          <button className="btn-primary mt-2 w-full" disabled={busy}>{busy ? 'Sending...' : 'Send reset instructions'}</button>
        </form>
      ) : (
        <form onSubmit={confirmReset}>
          <p className="mb-4 text-sm text-slate-600">
            If the email exists, reset instructions were sent. Enter the token from that message below. For local setups without email, check <code>backend/notification_log.txt</code>.
          </p>
          <Field label="Reset token">
            <input className="input" required value={token} onChange={(event) => setToken(event.target.value)} />
          </Field>
          <Field label="New password">
            <input className="input" type="password" minLength={8} required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
          </Field>
          <button className="btn-primary mt-2 w-full" disabled={busy}>{busy ? 'Updating...' : 'Set new password'}</button>
        </form>
      )}
      <p className="mt-5 text-center text-sm text-slate-500">
        Remembered it? <Link className="font-semibold text-brand-700 hover:text-brand-800" to="/login">Back to sign in</Link>
      </p>
    </AuthLayout>
  )
}

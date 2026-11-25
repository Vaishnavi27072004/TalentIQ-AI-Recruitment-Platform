// Small reusable UI pieces used on every page.
import { Loader2, Inbox, AlertTriangle, X } from 'lucide-react'
import { prettyStatus } from '../utils/format'

const BADGE_COLORS = {
  applied: 'bg-slate-100 text-slate-700', shortlisted: 'bg-blue-100 text-blue-700',
  approved_for_interview: 'bg-violet-100 text-violet-700', interview_scheduled: 'bg-amber-100 text-amber-700',
  selected: 'bg-emerald-100 text-emerald-700', rejected: 'bg-red-100 text-red-700',
  active: 'bg-emerald-100 text-emerald-700', closed: 'bg-slate-200 text-slate-600', draft: 'bg-amber-100 text-amber-700',
  scheduled: 'bg-blue-100 text-blue-700', completed: 'bg-emerald-100 text-emerald-700', cancelled: 'bg-red-100 text-red-700',
  failed: 'bg-red-100 text-red-700', processing: 'bg-amber-100 text-amber-700', duplicate: 'bg-orange-100 text-orange-700',
  'Strong Match': 'bg-emerald-100 text-emerald-700', 'Possible Match': 'bg-amber-100 text-amber-700',
  'Weak Match': 'bg-slate-100 text-slate-600', 'Not a Match': 'bg-red-100 text-red-700',
  'Strongly Recommended': 'bg-emerald-100 text-emerald-700', Recommended: 'bg-blue-100 text-blue-700',
  'On Hold': 'bg-amber-100 text-amber-700', 'Not Recommended': 'bg-red-100 text-red-700',
}

export function StatusBadge({ value }) {
  if (!value) return null
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${BADGE_COLORS[value] || 'bg-slate-100 text-slate-700'}`}>{prettyStatus(value)}</span>
}

export function Spinner({ label = 'Loading...' }) {
  return <div className="flex items-center justify-center gap-2 py-12 text-slate-500"><Loader2 className="animate-spin" size={18} />{label}</div>
}

export function EmptyState({ title, hint }) {
  return (
    <div className="flex flex-col items-center py-12 text-center text-slate-500">
      <Inbox size={32} className="mb-2 text-slate-300" />
      <p className="font-medium text-slate-600">{title}</p>
      {hint && <p className="text-sm">{hint}</p>}
    </div>
  )
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center py-10 text-center">
      <AlertTriangle className="mb-2 text-red-500" />
      <p className="text-sm text-red-600">{message}</p>
      {onRetry && <button className="btn-secondary mt-3" onClick={onRetry}>Try again</button>}
    </div>
  )
}

// Shows a spinner / error / the page body, so every page handles all three states the same way.
export function Loadable({ loading, error, reload, children }) {
  if (loading) return <Spinner />
  if (error) return <ErrorState message={error} onRetry={reload} />
  return children
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-navy-900 sm:text-[28px]">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      <div className="flex gap-2">{actions}</div>
    </div>
  )
}

export function Modal({ title, onClose, children, wide }) {
  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4">
      <div className={`mt-10 w-full rounded-2xl bg-white p-6 shadow-xl ${wide ? 'max-w-3xl' : 'max-w-lg'}`}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-navy-900">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700"><X size={20} /></button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function StatCard({ icon: Icon, label, value }) {
  return (
    <div className="card group flex items-center gap-4 transition duration-200 hover:-translate-y-0.5 hover:border-brand-100 hover:shadow-md">
      <div className="rounded-xl bg-brand-50 p-3 text-brand-600 transition group-hover:bg-brand-100"><Icon size={21} /></div>
      <div className="min-w-0">
        <p className="text-2xl font-bold tracking-tight text-navy-900">{value ?? '-'}</p>
        <p className="mt-0.5 text-xs font-medium text-slate-500">{label}</p>
      </div>
    </div>
  )
}

// Horizontal 0-100 bar used for the matching score breakdown.
export function ScoreBar({ label, score, weight }) {
  const isMissing = score === null || score === undefined
  const color = isMissing ? 'bg-slate-300' : score >= 75 ? 'bg-emerald-500' : score >= 50 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs text-slate-600">
        <span>{label} <span className="text-slate-400">({Math.round(weight * 100)}% weight)</span></span>
        <span className="font-semibold">{isMissing ? 'N/A (not in job)' : `${score}/100`}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100"><div className={`h-2 rounded-full ${color}`} style={{ width: `${isMissing ? 0 : score}%` }} /></div>
    </div>
  )
}

export function SkillChips({ skills, tone = 'slate' }) {
  const tones = { slate: 'bg-slate-100 text-slate-700', green: 'bg-emerald-100 text-emerald-700', red: 'bg-red-100 text-red-700' }
  if (!skills?.length) return <span className="text-sm text-slate-400">None</span>
  return <div className="flex flex-wrap gap-1.5">{skills.map((s) => <span key={s} className={`rounded-md px-2 py-0.5 text-xs ${tones[tone]}`}>{s}</span>)}</div>
}

export function Field({ label, children }) {
  return <div className="mb-3"><label className="label">{label}</label>{children}</div>
}

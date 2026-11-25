// Editable form for extracted resume data. Used by the candidate (own profile) and by admins.
import { useState } from 'react'
import { Save } from 'lucide-react'
import api, { errorMessage } from '../services/api'
import { useToast } from '../context/ToastContext'
import { Field } from './ui'
import { splitList } from '../utils/format'

// Lists of objects are edited as simple text lines to keep the form small:
//   education:  "Degree | Institution | Year"       experience: "Title | Company | Start | End"
const toLines = (items, keys) => (items || []).map((item) => keys.map((k) => item[k] ?? '').join(' | ')).join('\n')
const fromLines = (text, keys) =>
  text.split('\n').map((line) => line.trim()).filter(Boolean).map((line) => {
    const parts = line.split('|').map((p) => p.trim())
    return Object.fromEntries(keys.map((key, index) => [key, parts[index] || null]))
  })

const EDU_KEYS = ['degree', 'institution', 'year']
const JOB_KEYS = ['title', 'company', 'start', 'end']
const PROJECT_KEYS = ['name', 'description']

export default function CandidateEditor({ candidate, saveUrl, onSaved }) {
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    name: candidate.name || '', phone: candidate.phone || '', location: candidate.location || '',
    summary: candidate.summary || '', total_experience_years: candidate.total_experience_years ?? 0,
    technical_skills: (candidate.technical_skills || []).join(', '), soft_skills: (candidate.soft_skills || []).join(', '),
    certifications: (candidate.certifications || []).join(', '),
    education: toLines(candidate.education, EDU_KEYS), employment_history: toLines(candidate.employment_history, JOB_KEYS),
    projects: toLines(candidate.projects, PROJECT_KEYS),
  })
  const set = (field) => (event) => setForm({ ...form, [field]: event.target.value })

  async function handleSave(event) {
    event.preventDefault()
    setSaving(true)
    try {
      const payload = {
        name: form.name, phone: form.phone, location: form.location, summary: form.summary,
        total_experience_years: Number(form.total_experience_years) || 0,
        technical_skills: splitList(form.technical_skills), soft_skills: splitList(form.soft_skills),
        certifications: splitList(form.certifications),
        education: fromLines(form.education, EDU_KEYS), employment_history: fromLines(form.employment_history, JOB_KEYS),
        projects: fromLines(form.projects, PROJECT_KEYS),
      }
      const { data } = await api.put(saveUrl, payload)
      toast.success('Profile saved')
      onSaved?.(data)
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSave}>
      <div className="grid gap-x-4 md:grid-cols-2">
        <Field label="Name"><input className="input" value={form.name} onChange={set('name')} /></Field>
        <Field label="Email (cannot be changed)"><input className="input bg-slate-50" disabled value={candidate.email || ''} /></Field>
        <Field label="Phone"><input className="input" value={form.phone} onChange={set('phone')} /></Field>
        <Field label="Location"><input className="input" value={form.location} onChange={set('location')} /></Field>
        <Field label="Total experience (years)"><input className="input" type="number" min="0" max="60" step="0.5" value={form.total_experience_years} onChange={set('total_experience_years')} /></Field>
        <Field label="Certifications (comma separated)"><input className="input" value={form.certifications} onChange={set('certifications')} /></Field>
      </div>
      <Field label="Professional summary"><textarea className="input" rows={3} value={form.summary} onChange={set('summary')} /></Field>
      <Field label="Technical skills (comma separated)"><input className="input" value={form.technical_skills} onChange={set('technical_skills')} /></Field>
      <Field label="Soft skills (comma separated)"><input className="input" value={form.soft_skills} onChange={set('soft_skills')} /></Field>
      <Field label="Education (one per line: Degree | Institution | Year)"><textarea className="input" rows={3} value={form.education} onChange={set('education')} /></Field>
      <Field label="Employment history (one per line: Title | Company | Start | End)"><textarea className="input" rows={3} value={form.employment_history} onChange={set('employment_history')} /></Field>
      <Field label="Projects (one per line: Name | Description)"><textarea className="input" rows={3} value={form.projects} onChange={set('projects')} /></Field>
      <button className="btn-primary" disabled={saving}><Save size={16} />{saving ? 'Saving...' : 'Save changes'}</button>
    </form>
  )
}

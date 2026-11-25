import { useState } from 'react'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import api, { errorMessage } from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { useToast } from '../../context/ToastContext'
import { Loadable, PageHeader, Modal, Field, StatusBadge, EmptyState, SkillChips } from '../../components/ui'
import { splitList, formatDate } from '../../utils/format'

const EMPTY_FORM = {
  title: '', description: '', required_skills: '', preferred_skills: '', min_experience: 0, max_experience: '',
  education_requirement: '', location: '', employment_type: 'Full-time', deadline: '', status: 'active',
}

function JobForm({ job, onSaved, onClose }) {
  const toast = useToast()
  const [form, setForm] = useState(job ? {
    ...job, required_skills: job.required_skills.join(', '), preferred_skills: job.preferred_skills.join(', '),
    max_experience: job.max_experience ?? '', deadline: job.deadline || '',
  } : EMPTY_FORM)
  const set = (field) => (event) => setForm({ ...form, [field]: event.target.value })

  async function handleSubmit(event) {
    event.preventDefault()
    const payload = {
      title: form.title, description: form.description,
      required_skills: splitList(form.required_skills), preferred_skills: splitList(form.preferred_skills),
      min_experience: Number(form.min_experience) || 0, max_experience: form.max_experience === '' ? null : Number(form.max_experience),
      education_requirement: form.education_requirement, location: form.location, employment_type: form.employment_type,
      deadline: form.deadline || null, status: form.status,
    }
    try {
      if (job) await api.put(`/api/jobs/${job.id}`, payload)
      else await api.post('/api/jobs', payload)
      toast.success(job ? 'Job updated' : 'Job created')
      onSaved()
    } catch (error) { toast.error(errorMessage(error)) }
  }

  return (
    <form onSubmit={handleSubmit}>
      <Field label="Job title"><input className="input" required value={form.title} onChange={set('title')} /></Field>
      <Field label="Description"><textarea className="input" rows={4} required value={form.description} onChange={set('description')} /></Field>
      <Field label="Required skills (comma separated)"><input className="input" value={form.required_skills} onChange={set('required_skills')} /></Field>
      <Field label="Preferred skills (comma separated)"><input className="input" value={form.preferred_skills} onChange={set('preferred_skills')} /></Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Minimum experience (years)"><input className="input" type="number" min="0" step="0.5" value={form.min_experience} onChange={set('min_experience')} /></Field>
        <Field label="Maximum experience (years)"><input className="input" type="number" min="0" step="0.5" value={form.max_experience} onChange={set('max_experience')} /></Field>
        <Field label="Education requirement"><input className="input" placeholder="e.g. Bachelor's degree" value={form.education_requirement} onChange={set('education_requirement')} /></Field>
        <Field label="Location"><input className="input" value={form.location} onChange={set('location')} /></Field>
        <Field label="Employment type">
          <select className="input" value={form.employment_type} onChange={set('employment_type')}>{['Full-time', 'Part-time', 'Contract', 'Internship'].map((t) => <option key={t}>{t}</option>)}</select>
        </Field>
        <Field label="Last application date"><input className="input" type="date" value={form.deadline} onChange={set('deadline')} /></Field>
        <Field label="Status">
          <select className="input" value={form.status} onChange={set('status')}>{['active', 'closed', 'draft'].map((s) => <option key={s}>{s}</option>)}</select>
        </Field>
      </div>
      <div className="mt-2 flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary">Save job</button></div>
    </form>
  )
}

export default function Jobs() {
  const toast = useToast()
  const { data, loading, error, reload } = useFetch('/api/jobs')
  const [editing, setEditing] = useState(null) // null = closed, {} = new, job = edit

  async function handleDelete(job) {
    if (!window.confirm(`Delete "${job.title}" and its applications?`)) return
    try { await api.delete(`/api/jobs/${job.id}`); toast.success('Job deleted'); reload() }
    catch (error) { toast.error(errorMessage(error)) }
  }

  return (
    <>
      <PageHeader title="Jobs" subtitle="Create and manage openings" actions={<button className="btn-primary" onClick={() => setEditing({})}><Plus size={16} />New job</button>} />
      <Loadable loading={loading} error={error} reload={reload}>
        <div className="card overflow-x-auto p-0">
          {data?.length ? (
            <table className="w-full">
              <thead><tr><th className="th">Title</th><th className="th">Required skills</th><th className="th">Experience</th><th className="th">Location</th><th className="th">Deadline</th><th className="th">Applications</th><th className="th">Status</th><th className="th" /></tr></thead>
              <tbody>
                {data.map((job) => (
                  <tr key={job.id}>
                    <td className="td font-medium">{job.title}<div className="text-xs text-slate-400">{job.employment_type}</div></td>
                    <td className="td max-w-xs"><SkillChips skills={job.required_skills} /></td>
                    <td className="td">{job.min_experience}{job.max_experience != null ? `-${job.max_experience}` : '+'} yrs</td>
                    <td className="td">{job.location || '-'}</td>
                    <td className="td">{formatDate(job.deadline)}</td>
                    <td className="td">{job.application_count}</td>
                    <td className="td"><StatusBadge value={job.status} /></td>
                    <td className="td whitespace-nowrap">
                      <button className="mr-2 text-slate-500 hover:text-brand-600" title="Edit" onClick={() => setEditing(job)}><Pencil size={16} /></button>
                      <button className="text-slate-500 hover:text-red-600" title="Delete" onClick={() => handleDelete(job)}><Trash2 size={16} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <EmptyState title="No jobs yet" hint="Click New job to create the first one." />}
        </div>
      </Loadable>
      {editing && (
        <Modal title={editing.id ? 'Edit job' : 'New job'} onClose={() => setEditing(null)} wide>
          <JobForm job={editing.id ? editing : null} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); reload() }} />
        </Modal>
      )}
    </>
  )
}

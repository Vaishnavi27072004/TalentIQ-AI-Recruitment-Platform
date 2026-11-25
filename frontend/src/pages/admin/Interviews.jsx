import { useState } from 'react'
import { Plus, CalendarClock, Ban } from 'lucide-react'
import api, { errorMessage } from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { useToast } from '../../context/ToastContext'
import { Loadable, PageHeader, Modal, Field, StatusBadge, EmptyState } from '../../components/ui'
import { formatDateTime } from '../../utils/format'

function localDateTimeMin() {
  const now = new Date()
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
  return now.toISOString().slice(0, 16)
}

function ScheduleForm({ onSaved, onClose }) {
  const toast = useToast()
  const applications = useFetch('/api/applications')
  const interviewers = useFetch('/api/auth/interviewers')
  const [form, setForm] = useState({ application_id: '', interviewer_id: '', scheduled_at: '', duration_minutes: 45, interview_type: 'Technical', meeting_link: '' })
  const set = (field) => (event) => setForm({ ...form, [field]: event.target.value })
  // Only candidates already approved for interview can be scheduled.
  const approved = (applications.data || []).filter((a) => ['approved_for_interview', 'interview_scheduled'].includes(a.status))

  async function handleSubmit(event) {
    event.preventDefault()
    try {
      await api.post('/api/interviews', {
        ...form, scheduled_at: new Date(form.scheduled_at).toISOString(),
        application_id: Number(form.application_id), interviewer_id: Number(form.interviewer_id),
        duration_minutes: Number(form.duration_minutes),
      })
      toast.success('Interview scheduled. Candidate and interviewer notified.')
      onSaved()
    } catch (error) { toast.error(errorMessage(error)) }
  }

  return (
    <form onSubmit={handleSubmit}>
      <Field label="Candidate (approved for interview)">
        <select className="input" required value={form.application_id} onChange={set('application_id')}>
          <option value="">Choose...</option>
          {approved.map((a) => <option key={a.id} value={a.id}>{a.candidate_name} - {a.job_title}</option>)}
        </select>
      </Field>
      {approved.length === 0 && !applications.loading && <p className="mb-3 text-xs text-amber-600">No approved candidates. Approve someone in Shortlists first.</p>}
      <Field label="Interviewer">
        <select className="input" required value={form.interviewer_id} onChange={set('interviewer_id')}>
          <option value="">Choose...</option>
          {interviewers.data?.map((i) => <option key={i.id} value={i.id}>{i.full_name}</option>)}
        </select>
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Date and time"><input className="input" type="datetime-local" min={localDateTimeMin()} required value={form.scheduled_at} onChange={set('scheduled_at')} /></Field>
        <Field label="Duration (minutes)"><input className="input" type="number" min="10" max="240" value={form.duration_minutes} onChange={set('duration_minutes')} /></Field>
        <Field label="Interview type"><select className="input" value={form.interview_type} onChange={set('interview_type')}>{['Technical', 'HR', 'Managerial', 'Final'].map((t) => <option key={t}>{t}</option>)}</select></Field>
        <Field label="Meeting link"><input className="input" placeholder="https://..." value={form.meeting_link} onChange={set('meeting_link')} /></Field>
      </div>
      <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary">Schedule</button></div>
    </form>
  )
}

export default function Interviews() {
  const toast = useToast()
  const { data, loading, error, reload } = useFetch('/api/interviews')
  const [showForm, setShowForm] = useState(false)
  const [reschedule, setReschedule] = useState(null)
  const [newTime, setNewTime] = useState('')

  async function cancel(interview) {
    if (!window.confirm('Cancel this interview?')) return
    try { await api.post(`/api/interviews/${interview.id}/cancel`); toast.success('Interview cancelled'); reload() }
    catch (err) { toast.error(errorMessage(err)) }
  }

  async function saveReschedule() {
    try { await api.put(`/api/interviews/${reschedule.id}/reschedule`, { scheduled_at: new Date(newTime).toISOString() }); toast.success('Interview rescheduled'); setReschedule(null); reload() }
    catch (err) { toast.error(errorMessage(err)) }
  }

  const now = new Date()
  const upcoming = (data || []).filter((i) => i.status === 'scheduled' && new Date(i.scheduled_at) >= now).length

  return (
    <>
      <PageHeader title="Interviews" subtitle={`${upcoming} upcoming`} actions={<button className="btn-primary" onClick={() => setShowForm(true)}><Plus size={16} />Schedule interview</button>} />
      <Loadable loading={loading} error={error} reload={reload}>
        <div className="card overflow-x-auto p-0">
          {data?.length ? (
            <table className="w-full">
              <thead><tr><th className="th">When</th><th className="th">Candidate</th><th className="th">Job</th><th className="th">Interviewer</th><th className="th">Type</th><th className="th">Status</th><th className="th">Feedback</th><th className="th" /></tr></thead>
              <tbody>
                {data.map((i) => (
                  <tr key={i.id}>
                    <td className="td whitespace-nowrap">{formatDateTime(i.scheduled_at)}<div className="text-xs text-slate-400">{i.duration_minutes} min</div></td>
                    <td className="td font-medium">{i.candidate_name}</td>
                    <td className="td">{i.job_title}</td>
                    <td className="td">{i.interviewer_name}</td>
                    <td className="td">{i.interview_type}</td>
                    <td className="td"><StatusBadge value={i.status} /></td>
                    <td className="td text-xs">
                      {i.feedback ? <><StatusBadge value={i.feedback.recommendation} /><div className="mt-1 text-slate-500">T {i.feedback.technical_score} | C {i.feedback.communication_score} | P {i.feedback.problem_solving_score}</div>{i.feedback.remarks && <div className="mt-1 max-w-[220px] text-slate-600">{i.feedback.remarks}</div>}</> : '-'}
                    </td>
                    <td className="td whitespace-nowrap">
                      {i.status === 'scheduled' && <>
                        <button className="mr-2 text-slate-500 hover:text-brand-600" title="Reschedule" onClick={() => { setReschedule(i); setNewTime('') }}><CalendarClock size={16} /></button>
                        <button className="text-slate-500 hover:text-red-600" title="Cancel" onClick={() => cancel(i)}><Ban size={16} /></button>
                      </>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <EmptyState title="No interviews scheduled" hint="Approve a shortlisted candidate, then schedule an interview." />}
        </div>
      </Loadable>

      {showForm && <Modal title="Schedule interview" onClose={() => setShowForm(false)}><ScheduleForm onClose={() => setShowForm(false)} onSaved={() => { setShowForm(false); reload() }} /></Modal>}
      {reschedule && (
        <Modal title={`Reschedule: ${reschedule.candidate_name}`} onClose={() => setReschedule(null)}>
          <Field label="New date and time"><input className="input" type="datetime-local" min={localDateTimeMin()} value={newTime} onChange={(e) => setNewTime(e.target.value)} /></Field>
          <button className="btn-primary" disabled={!newTime} onClick={saveReschedule}>Save new time</button>
        </Modal>
      )}
    </>
  )
}

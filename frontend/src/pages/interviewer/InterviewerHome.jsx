import { useState } from 'react'
import { Eye, MessageSquarePlus } from 'lucide-react'
import api, { errorMessage } from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { useToast } from '../../context/ToastContext'
import { Loadable, PageHeader, Modal, Field, StatusBadge, EmptyState, Spinner } from '../../components/ui'
import CandidateSummary from '../../components/CandidateSummary'
import { formatDateTime, RECOMMENDATIONS } from '../../utils/format'

function CandidateModal({ candidateId, onClose }) {
  const { data, loading, error } = useFetch(`/api/candidates/${candidateId}`)
  return (
    <Modal title="Candidate profile" onClose={onClose} wide>
      {loading ? <Spinner /> : error ? <p className="text-sm text-red-600">{error}</p> : <CandidateSummary candidate={data} />}
    </Modal>
  )
}

function FeedbackForm({ interview, onSaved, onClose }) {
  const toast = useToast()
  const [form, setForm] = useState({ technical_score: 3, communication_score: 3, problem_solving_score: 3, remarks: '', recommendation: 'Recommended' })
  const set = (field) => (event) => setForm({ ...form, [field]: event.target.value })
  const score = (field, label) => (
    <Field label={`${label} (1-5)`}><select className="input" value={form[field]} onChange={set(field)}>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}</select></Field>
  )

  async function handleSubmit(event) {
    event.preventDefault()
    try {
      await api.post(`/api/interviews/${interview.id}/feedback`, {
        ...form, technical_score: Number(form.technical_score), communication_score: Number(form.communication_score), problem_solving_score: Number(form.problem_solving_score),
      })
      toast.success('Feedback submitted')
      onSaved()
    } catch (error) { toast.error(errorMessage(error)) }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="grid grid-cols-3 gap-3">{score('technical_score', 'Technical skills')}{score('communication_score', 'Communication')}{score('problem_solving_score', 'Problem solving')}</div>
      <Field label="Remarks"><textarea className="input" rows={4} value={form.remarks} onChange={set('remarks')} /></Field>
      <Field label="Final recommendation"><select className="input" value={form.recommendation} onChange={set('recommendation')}>{RECOMMENDATIONS.map((r) => <option key={r}>{r}</option>)}</select></Field>
      <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary">Submit feedback</button></div>
    </form>
  )
}

export default function InterviewerHome() {
  const { data, loading, error, reload } = useFetch('/api/interviews')
  const [viewCandidate, setViewCandidate] = useState(null)
  const [feedbackFor, setFeedbackFor] = useState(null)

  return (
    <>
      <PageHeader title="My interviews" subtitle="Interviews assigned to you" />
      <Loadable loading={loading} error={error} reload={reload}>
        <div className="card overflow-x-auto p-0">
          {data?.length ? (
            <table className="w-full">
              <thead><tr><th className="th">When</th><th className="th">Candidate</th><th className="th">Job</th><th className="th">Type</th><th className="th">Status</th><th className="th" /></tr></thead>
              <tbody>
                {data.map((i) => (
                  <tr key={i.id}>
                    <td className="td whitespace-nowrap">{formatDateTime(i.scheduled_at)}<div className="text-xs text-slate-400">{i.duration_minutes} min</div></td>
                    <td className="td font-medium">{i.candidate_name}</td>
                    <td className="td">{i.job_title}</td>
                    <td className="td">{i.interview_type}{i.meeting_link && <a className="block text-xs text-brand-600" href={i.meeting_link} target="_blank" rel="noreferrer">Meeting link</a>}</td>
                    <td className="td"><StatusBadge value={i.status} />{i.feedback && <div className="mt-1"><StatusBadge value={i.feedback.recommendation} /></div>}</td>
                    <td className="td whitespace-nowrap">
                      <button className="btn-secondary mr-2" onClick={() => setViewCandidate(i.candidate_id)}><Eye size={15} />Profile</button>
                      {i.status === 'scheduled' && !i.has_feedback && <button className="btn-primary" onClick={() => setFeedbackFor(i)}><MessageSquarePlus size={15} />Feedback</button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <EmptyState title="No interviews assigned yet" />}
        </div>
      </Loadable>
      {viewCandidate && <CandidateModal candidateId={viewCandidate} onClose={() => setViewCandidate(null)} />}
      {feedbackFor && (
        <Modal title={`Feedback: ${feedbackFor.candidate_name}`} onClose={() => setFeedbackFor(null)}>
          <FeedbackForm interview={feedbackFor} onClose={() => setFeedbackFor(null)} onSaved={() => { setFeedbackFor(null); reload() }} />
        </Modal>
      )}
    </>
  )
}

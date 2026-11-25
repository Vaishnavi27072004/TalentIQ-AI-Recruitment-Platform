import { useState, useEffect } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { ArrowLeft, Download, Pencil } from 'lucide-react'
import api, { downloadFile, errorMessage } from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { useToast } from '../../context/ToastContext'
import { Loadable, PageHeader, Spinner, Field } from '../../components/ui'
import CandidateSummary from '../../components/CandidateSummary'
import CandidateEditor from '../../components/CandidateEditor'
import MatchPanel from '../../components/MatchPanel'

export default function CandidateProfile() {
  const { id } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()
  const { data: candidate, loading, error, reload } = useFetch(`/api/candidates/${id}`)
  const jobs = useFetch('/api/jobs')
  const [editing, setEditing] = useState(false)
  const [notes, setNotes] = useState('')
  const [jobId, setJobId] = useState(searchParams.get('job') || '')
  const [match, setMatch] = useState(null)
  const [matchLoading, setMatchLoading] = useState(false)

  useEffect(() => { if (candidate) setNotes(candidate.admin_notes || '') }, [candidate])

  async function loadMatch() {
    if (!jobId) { setMatch(null); return }
    setMatchLoading(true)
    try {
      const { data } = await api.get(`/api/matching/jobs/${jobId}/candidates/${id}`)
      setMatch(data)
    } catch (err) { toast.error(errorMessage(err)) } finally { setMatchLoading(false) }
  }
  useEffect(() => { loadMatch() }, [jobId, id]) // eslint-disable-line react-hooks/exhaustive-deps

  async function saveNotes() {
    try { await api.put(`/api/candidates/${id}/notes`, { admin_notes: notes }); toast.success('Notes saved') }
    catch (err) { toast.error(errorMessage(err)) }
  }

  async function shortlist() {
    try { await api.post('/api/shortlist', { job_id: Number(jobId), candidate_ids: [Number(id)] }); toast.success('Candidate shortlisted') }
    catch (err) { toast.error(errorMessage(err)) }
  }

  return (
    <>
      <PageHeader title="Candidate profile"
        actions={<Link to="/admin/candidates" className="btn-secondary"><ArrowLeft size={15} />Back</Link>} />
      <Loadable loading={loading} error={error} reload={reload}>
        {candidate && (
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="card">
              <div className="mb-3 flex flex-wrap gap-2">
                <button className="btn-secondary" onClick={() => setEditing(!editing)}><Pencil size={15} />{editing ? 'Cancel edit' : 'Correct extracted info'}</button>
                {candidate.resumes.filter((r) => r.status === 'completed').map((r) => (
                  <button key={r.id} className="btn-secondary" onClick={() => downloadFile(`/api/candidates/resumes/${r.id}/download`, r.filename)}><Download size={15} />{r.filename}</button>
                ))}
              </div>
              {editing
                ? <CandidateEditor candidate={candidate} saveUrl={`/api/candidates/${id}`} onSaved={() => { setEditing(false); reload() }} />
                : <CandidateSummary candidate={candidate} />}
              <div className="mt-4 border-t pt-4">
                <Field label="Internal notes (never visible to the candidate)">
                  <textarea className="input" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
                </Field>
                <button className="btn-secondary" onClick={saveNotes}>Save notes</button>
              </div>
            </div>

            <div className="card">
              <h3 className="mb-3 font-semibold text-navy-900">AI match explanation</h3>
              <Field label="Compare against job">
                <select className="input" value={jobId} onChange={(e) => { setJobId(e.target.value); setSearchParams(e.target.value ? { job: e.target.value } : {}) }}>
                  <option value="">Select a job...</option>
                  {jobs.data?.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
                </select>
              </Field>
              {matchLoading ? <Spinner label="Calculating match..." /> : match
                ? <><MatchPanel match={match} onChanged={loadMatch} /><button className="btn-primary mt-4" onClick={shortlist}>Shortlist for this job</button></>
                : <p className="text-sm text-slate-500">Pick a job to see the score, matched/missing skills and explanation.</p>}
            </div>
          </div>
        )}
      </Loadable>
    </>
  )
}

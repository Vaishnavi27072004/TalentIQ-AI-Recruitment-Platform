import { useState } from 'react'
import { Sparkles, ListChecks } from 'lucide-react'
import api, { errorMessage } from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { useToast } from '../../context/ToastContext'
import { PageHeader, Modal, StatusBadge, EmptyState, Spinner, Field } from '../../components/ui'
import MatchPanel from '../../components/MatchPanel'

export default function Matching() {
  const toast = useToast()
  const jobs = useFetch('/api/jobs')
  const [jobId, setJobId] = useState('')
  const [results, setResults] = useState(null)
  const [running, setRunning] = useState(false)
  const [selected, setSelected] = useState([])
  const [openMatch, setOpenMatch] = useState(null)

  async function runMatching() {
    setRunning(true)
    setSelected([])
    try {
      const { data } = await api.post(`/api/matching/jobs/${jobId}/run`)
      setResults(data)
    } catch (error) { toast.error(errorMessage(error)) } finally { setRunning(false) }
  }

  async function shortlistSelected() {
    try {
      await api.post('/api/shortlist', { job_id: Number(jobId), candidate_ids: selected })
      toast.success(`${selected.length} candidate(s) shortlisted`)
      setSelected([])
    } catch (error) { toast.error(errorMessage(error)) }
  }

  const toggle = (id) => setSelected((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]))
  const refreshOpenMatch = async () => {
    const { data } = await api.get(`/api/matching/jobs/${jobId}`)
    setResults(data)
    setOpenMatch(data.find((m) => m.match_id === openMatch.match_id))
  }

  return (
    <>
      <PageHeader title="AI Matching" subtitle="Match percentage is the share of required skills found in each resume; other fit signals are shown in the breakdown." />
      <div className="card mb-4 flex flex-wrap items-end gap-3">
        <div className="min-w-[240px] flex-1">
          <Field label="Select a job">
            <select className="input" value={jobId} onChange={(e) => { setJobId(e.target.value); setResults(null) }}>
              <option value="">Choose...</option>
              {jobs.data?.map((j) => <option key={j.id} value={j.id}>{j.title} ({j.status})</option>)}
            </select>
          </Field>
        </div>
        <button className="btn-primary mb-3" disabled={!jobId || running} onClick={runMatching}><Sparkles size={16} />{running ? 'Matching...' : 'Find matching candidates'}</button>
        {selected.length > 0 && <button className="btn-secondary mb-3" onClick={shortlistSelected}><ListChecks size={16} />Shortlist {selected.length} selected</button>}
      </div>

      {running && <Spinner label="Scoring every candidate..." />}
      {results && !running && (
        <div className="card overflow-x-auto p-0">
          {results.length ? (
            <table className="w-full">
              <thead><tr><th className="th" /><th className="th">Rank</th><th className="th">Candidate</th><th className="th">Score</th><th className="th">Skills</th><th className="th">Missing skills</th><th className="th">Recommendation</th><th className="th" /></tr></thead>
              <tbody>
                {results.map((m, index) => (
                  <tr key={m.match_id} className="hover:bg-slate-50">
                    <td className="td"><input type="checkbox" checked={selected.includes(m.candidate_id)} onChange={() => toggle(m.candidate_id)} /></td>
                    <td className="td">{index + 1}</td>
                    <td className="td font-medium">{m.name || m.email}</td>
                    <td className="td"><b>{m.final_score}%</b></td>
                    <td className="td">{m.details.scores.skills ?? '-'}</td>
                    <td className="td text-xs text-red-600">{m.details.missing_skills.join(', ') || '-'}</td>
                    <td className="td"><StatusBadge value={m.effective_recommendation} /></td>
                    <td className="td"><button className="btn-secondary" onClick={() => setOpenMatch(m)}>Explain</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <EmptyState title="No candidates to match yet" hint="Upload resumes first." />}
        </div>
      )}

      {openMatch && (
        <Modal title={`${openMatch.name} - match details`} onClose={() => setOpenMatch(null)} wide>
          <MatchPanel match={openMatch} onChanged={refreshOpenMatch} />
        </Modal>
      )}
    </>
  )
}

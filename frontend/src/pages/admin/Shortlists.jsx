import { useState } from 'react'
import { Download, Share2, UserCheck, X } from 'lucide-react'
import api, { downloadFile, errorMessage } from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { useToast } from '../../context/ToastContext'
import { Loadable, PageHeader, StatusBadge, EmptyState } from '../../components/ui'
import { APPLICATION_STATUSES, prettyStatus } from '../../utils/format'

export default function Shortlists() {
  const toast = useToast()
  const jobs = useFetch('/api/jobs')
  const [jobId, setJobId] = useState('')
  const { data, loading, error, reload } = useFetch('/api/shortlist', jobId ? { job_id: jobId } : {})
  const [shareLink, setShareLink] = useState('')

  async function act(request, successMessage) {
    try { await request(); toast.success(successMessage); reload() }
    catch (err) { toast.error(errorMessage(err)) }
  }

  async function createShareLink() {
    try {
      const { data: share } = await api.post(`/api/shortlist/share/${jobId}`)
      setShareLink(`${api.defaults.baseURL}${share.path}`)
    } catch (err) { toast.error(errorMessage(err)) }
  }

  return (
    <>
      <PageHeader title="Shortlists" subtitle="You make the final decision. AI only recommends."
        actions={<>
          <button className="btn-secondary" onClick={() => downloadFile(`/api/shortlist/export?format=csv${jobId ? `&job_id=${jobId}` : ''}`, 'shortlist.csv')}><Download size={15} />CSV</button>
          <button className="btn-secondary" onClick={() => downloadFile(`/api/shortlist/export?format=xlsx${jobId ? `&job_id=${jobId}` : ''}`, 'shortlist.xlsx')}><Download size={15} />Excel</button>
          <button className="btn-secondary" disabled={!jobId} title={jobId ? '' : 'Select a job first'} onClick={createShareLink}><Share2 size={15} />Share link</button>
        </>} />
      <div className="card mb-4">
        <select className="input max-w-sm" value={jobId} onChange={(e) => { setJobId(e.target.value); setShareLink('') }}>
          <option value="">All jobs</option>
          {jobs.data?.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
        </select>
        {shareLink && <p className="mt-3 break-all rounded bg-slate-50 p-2 text-xs">Expires in 48 hours, shows names, skills and scores only (no emails or notes): {shareLink}</p>}
      </div>

      <Loadable loading={loading} error={error} reload={reload}>
        <div className="card overflow-x-auto p-0">
          {data?.length ? (
            <table className="w-full">
              <thead><tr><th className="th">Candidate</th><th className="th">Job</th><th className="th">Score</th><th className="th">Recommendation</th><th className="th">Status</th><th className="th">Actions</th></tr></thead>
              <tbody>
                {data.map((row) => (
                  <tr key={row.id}>
                    <td className="td font-medium">{row.candidate_name}<div className="text-xs text-slate-400">{row.candidate_email}</div></td>
                    <td className="td">{row.job_title}</td>
                    <td className="td">{row.match_score ?? '-'}</td>
                    <td className="td"><StatusBadge value={row.recommendation} /></td>
                    <td className="td">
                      <select className="input py-1" value={row.status} onChange={(e) => act(() => api.put(`/api/applications/${row.id}/status`, { status: e.target.value }), 'Status updated')}>
                        {APPLICATION_STATUSES.map((s) => <option key={s} value={s}>{prettyStatus(s)}</option>)}
                      </select>
                    </td>
                    <td className="td whitespace-nowrap">
                      {row.status === 'shortlisted' && <button className="btn-primary mr-2" onClick={() => act(() => api.post(`/api/shortlist/${row.id}/approve`), 'Approved. Candidate notified.')}><UserCheck size={14} />Approve for interview</button>}
                      <button className="btn-secondary" onClick={() => act(() => api.delete(`/api/shortlist/${row.id}`), 'Removed from shortlist')}><X size={14} />Remove</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <EmptyState title="Nobody shortlisted yet" hint="Shortlist candidates from AI Matching or a candidate profile." />}
        </div>
      </Loadable>
    </>
  )
}

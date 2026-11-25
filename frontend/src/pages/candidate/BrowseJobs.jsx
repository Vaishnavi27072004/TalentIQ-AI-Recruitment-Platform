import { useState } from 'react'
import { MapPin, Clock } from 'lucide-react'
import api, { errorMessage } from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { useToast } from '../../context/ToastContext'
import { Loadable, PageHeader, Modal, EmptyState, SkillChips, StatusBadge } from '../../components/ui'
import { formatDate } from '../../utils/format'

export default function BrowseJobs() {
  const toast = useToast()
  const jobs = useFetch('/api/jobs')
  const applications = useFetch('/api/applications/me')
  const [openJob, setOpenJob] = useState(null)
  const applicationFor = (jobId) => applications.data?.find((a) => a.job_id === jobId)

  async function apply(job) {
    try {
      await api.post(`/api/jobs/${job.id}/apply`)
      toast.success(`Applied to ${job.title}`)
      applications.reload()
    } catch (err) { toast.error(errorMessage(err)) }
  }

  return (
    <>
      <PageHeader title="Open jobs" subtitle="Apply with the profile you saved" />
      <Loadable loading={jobs.loading} error={jobs.error} reload={jobs.reload}>
        {jobs.data?.length ? (
          <div className="grid gap-4 md:grid-cols-2">
            {jobs.data.map((job) => {
              const existing = applicationFor(job.id)
              return (
                <div key={job.id} className="card">
                  <h3 className="text-lg font-semibold text-navy-900">{job.title}</h3>
                  <p className="mt-1 flex flex-wrap gap-3 text-xs text-slate-500">
                    <span className="flex items-center gap-1"><MapPin size={12} />{job.location || 'Not specified'}</span>
                    <span>{job.employment_type}</span>
                    <span className="flex items-center gap-1"><Clock size={12} />{job.min_experience}{job.max_experience != null ? `-${job.max_experience}` : '+'} yrs</span>
                  </p>
                  <p className="mt-3 line-clamp-3 text-sm text-slate-600">{job.description}</p>
                  <div className="mt-3"><SkillChips skills={job.required_skills} /></div>
                  <div className="mt-4 flex items-center gap-2">
                    <button className="btn-secondary" onClick={() => setOpenJob(job)}>Details</button>
                    {existing ? <StatusBadge value={existing.status} /> : <button className="btn-primary" onClick={() => apply(job)}>Apply</button>}
                  </div>
                </div>
              )
            })}
          </div>
        ) : <EmptyState title="No open jobs right now" hint="Check back soon." />}
      </Loadable>
      {openJob && (
        <Modal title={openJob.title} onClose={() => setOpenJob(null)} wide>
          <p className="whitespace-pre-line text-sm">{openJob.description}</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div><p className="label">Required skills</p><SkillChips skills={openJob.required_skills} /></div>
            <div><p className="label">Preferred skills</p><SkillChips skills={openJob.preferred_skills} /></div>
            <div><p className="label">Education</p><p className="text-sm">{openJob.education_requirement || 'Not specified'}</p></div>
            <div><p className="label">Apply before</p><p className="text-sm">{formatDate(openJob.deadline)}</p></div>
          </div>
        </Modal>
      )}
    </>
  )
}

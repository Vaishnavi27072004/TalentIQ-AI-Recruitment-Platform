import { Video } from 'lucide-react'
import useFetch from '../../hooks/useFetch'
import { Loadable, PageHeader, StatusBadge, EmptyState } from '../../components/ui'
import { formatDateTime } from '../../utils/format'

export default function MyInterviews() {
  const { data, loading, error, reload } = useFetch('/api/interviews')
  return (
    <>
      <PageHeader title="My interviews" subtitle="Your scheduled interviews and meeting links" />
      <Loadable loading={loading} error={error} reload={reload}>
        {data?.length ? (
          <div className="space-y-3">
            {data.map((i) => (
              <div key={i.id} className="card flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-semibold text-navy-900">{i.job_title}</p>
                  <p className="text-sm text-slate-600">{formatDateTime(i.scheduled_at)} | {i.duration_minutes} min | {i.interview_type}</p>
                  <p className="text-xs text-slate-400">Interviewer: {i.interviewer_name}</p>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge value={i.status} />
                  {i.meeting_link && i.status === 'scheduled' && <a className="btn-primary" href={i.meeting_link} target="_blank" rel="noreferrer"><Video size={15} />Join</a>}
                </div>
              </div>
            ))}
          </div>
        ) : <EmptyState title="No interviews scheduled" hint="You will be notified when one is booked." />}
      </Loadable>
    </>
  )
}

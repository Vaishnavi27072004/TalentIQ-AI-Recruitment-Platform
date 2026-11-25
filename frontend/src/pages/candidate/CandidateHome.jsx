import { Link } from 'react-router-dom'
import api from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { Loadable, PageHeader, StatusBadge, EmptyState } from '../../components/ui'
import { formatDateTime } from '../../utils/format'

export default function CandidateHome() {
  const applications = useFetch('/api/applications/me')
  const notifications = useFetch('/api/notifications')

  async function markRead() {
    await api.post('/api/notifications/read-all')
    notifications.reload()
  }

  return (
    <>
      <PageHeader title="My dashboard" subtitle="Track your applications and updates" />
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <h3 className="mb-3 font-semibold text-navy-900">My applications</h3>
          <Loadable loading={applications.loading} error={applications.error} reload={applications.reload}>
            {applications.data?.length ? applications.data.map((a) => (
              <div key={a.id} className="flex items-center justify-between border-t border-slate-100 py-3 first:border-0">
                <div><p className="font-medium">{a.job_title}</p><p className="text-xs text-slate-400">Applied {formatDateTime(a.applied_at)}</p></div>
                <StatusBadge value={a.status} />
              </div>
            )) : <EmptyState title="No applications yet" hint="Upload your resume, then apply to a job." />}
          </Loadable>
          <Link to="/candidate/jobs" className="btn-primary mt-3">Browse jobs</Link>
        </div>

        <div className="card">
          <div className="mb-3 flex items-center justify-between"><h3 className="font-semibold text-navy-900">Notifications</h3><button className="text-xs text-brand-600" onClick={markRead}>Mark all read</button></div>
          <Loadable loading={notifications.loading} error={notifications.error} reload={notifications.reload}>
            {notifications.data?.length ? notifications.data.map((n) => (
              <div key={n.id} className={`border-t border-slate-100 py-2 text-sm first:border-0 ${n.is_read ? 'text-slate-500' : 'font-medium text-navy-900'}`}>
                {n.message}<div className="text-xs font-normal text-slate-400">{formatDateTime(n.created_at)}</div>
              </div>
            )) : <EmptyState title="No notifications" />}
          </Loadable>
        </div>
      </div>
    </>
  )
}

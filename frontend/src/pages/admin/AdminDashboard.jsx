import { Users, FileText, Briefcase, Inbox, ListChecks, CalendarClock, BadgeCheck } from 'lucide-react'
import useFetch from '../../hooks/useFetch'
import { Loadable, PageHeader, StatCard } from '../../components/ui'
import { ChartCard, SimpleBar, SimplePie } from '../../components/Charts'
import { prettyStatus } from '../../utils/format'

export default function AdminDashboard() {
  const { data, loading, error, reload } = useFetch('/api/analytics/dashboard')
  return (
    <>
      <PageHeader title="Dashboard" subtitle="Live numbers from the recruitment database" />
      <Loadable loading={loading} error={error} reload={reload}>
        {data && (
          <>
            <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard icon={Users} label="Total candidates" value={data.kpis.total_candidates} />
              <StatCard icon={FileText} label="Total resumes" value={data.kpis.total_resumes} />
              <StatCard icon={Briefcase} label="Active jobs" value={data.kpis.active_jobs} />
              <StatCard icon={Inbox} label="Total applications" value={data.kpis.total_applications} />
              <StatCard icon={ListChecks} label="Shortlisted candidates" value={data.kpis.shortlisted_candidates} />
              <StatCard icon={CalendarClock} label="Interviews scheduled" value={data.kpis.scheduled_interviews} />
              <StatCard icon={BadgeCheck} label="Selected candidates" value={data.kpis.selected_candidates} />
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <ChartCard title="Applications by job"><SimpleBar rows={data.applications_by_job} xKey="job" yKey="applications" horizontal /></ChartCard>
              <ChartCard title="Application statuses">
                <SimplePie rows={data.application_statuses.map((s) => ({ ...s, status: prettyStatus(s.status) }))} nameKey="status" valueKey="count" />
              </ChartCard>
            </div>
          </>
        )}
      </Loadable>
    </>
  )
}

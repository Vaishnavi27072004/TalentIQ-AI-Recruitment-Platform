import { useMemo, useState } from 'react'
import useFetch from '../../hooks/useFetch'
import { Loadable, PageHeader } from '../../components/ui'
import { ChartCard, SimpleBar, SimplePie } from '../../components/Charts'
import { prettyStatus } from '../../utils/format'

function dateRangeParams(range) {
  const params = {}
  if (range.start) params.start_at = new Date(`${range.start}T00:00:00`).toISOString()
  if (range.end) {
    const end = new Date(`${range.end}T00:00:00`)
    end.setDate(end.getDate() + 1)
    params.end_at = end.toISOString()
  }
  return params
}

export default function Analytics() {
  const [range, setRange] = useState({ start: '', end: '' })
  const [appliedRange, setAppliedRange] = useState({ start: '', end: '' })
  const [dateError, setDateError] = useState('')
  const params = useMemo(() => dateRangeParams(appliedRange), [appliedRange])
  const { data, loading, error, reload } = useFetch('/api/analytics/dashboard', params)

  function applyDateRange(event) {
    event.preventDefault()
    if (range.start && range.end && range.start > range.end) {
      setDateError('The start date must be on or before the end date.')
      return
    }
    setDateError('')
    setAppliedRange(range)
  }

  function clearDateRange() {
    const emptyRange = { start: '', end: '' }
    setRange(emptyRange)
    setAppliedRange(emptyRange)
    setDateError('')
  }

  return (
    <>
      <PageHeader title="Analytics" subtitle="Recruitment funnel, interviews and resume processing" />
      <form className="card mb-5" onSubmit={applyDateRange}>
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-full sm:w-44">
            <label htmlFor="analytics-start-date" className="label">From</label>
            <input id="analytics-start-date" type="date" className="input" value={range.start}
              onChange={(event) => setRange({ ...range, start: event.target.value })} />
          </div>
          <div className="w-full sm:w-44">
            <label htmlFor="analytics-end-date" className="label">To</label>
            <input id="analytics-end-date" type="date" className="input" value={range.end}
              onChange={(event) => setRange({ ...range, end: event.target.value })} />
          </div>
          <button type="submit" className="btn-primary">Apply dates</button>
          <button type="button" className="btn-secondary" onClick={clearDateRange}>Clear</button>
        </div>
        <p className="mt-3 text-xs leading-5 text-slate-500">
          Dates use your local timezone. Applications, job counts, statuses and funnel use application dates; interviews use scheduled dates; resumes use upload dates. Funnel stages show current progress.
        </p>
        {dateError && <p role="alert" className="mt-2 text-sm text-red-600">{dateError}</p>}
      </form>

      <Loadable loading={loading} error={error} reload={reload}>
        {data && (
          <>
            <section aria-label="Application conversion rates" className="mb-5">
              <h2 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">Application conversion rates</h2>
              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  ['Shortlist rate', data.conversion_rates.shortlisted, 'Shortlisted'],
                  ['Completed interview rate', data.conversion_rates.interviewed, 'Interviewed'],
                  ['Selection rate', data.conversion_rates.selected, 'Selected'],
                ].map(([label, rate, stage]) => {
                  const count = data.funnel.find((item) => item.stage === stage)?.count ?? 0
                  const total = data.funnel.find((item) => item.stage === 'Applied')?.count ?? 0
                  return (
                    <div key={label} className="card p-4">
                      <p className="text-xs font-medium text-slate-500">{label}</p>
                      <p className="mt-1 text-2xl font-bold tracking-tight text-navy-900">{rate.toFixed(1)}%</p>
                      <p className="mt-1 text-xs text-slate-400">{count} of {total} applications</p>
                    </div>
                  )
                })}
              </div>
              <p className="mt-2 text-xs text-slate-400">Rates use applications in the selected period as the denominator.</p>
            </section>
            <div className="grid gap-4 lg:grid-cols-2">
              <ChartCard title="Recruitment funnel"><SimpleBar rows={data.funnel} xKey="stage" yKey="count" horizontal /></ChartCard>
              <ChartCard title="Interview statistics"><SimpleBar rows={data.interview_stats} xKey="status" yKey="count" /></ChartCard>
              <ChartCard title="Applications by job"><SimpleBar rows={data.applications_by_job} xKey="job" yKey="applications" horizontal /></ChartCard>
              <ChartCard title="Application statuses">
                <SimplePie rows={data.application_statuses.map((status) => ({ ...status, status: prettyStatus(status.status) }))} nameKey="status" valueKey="count" />
              </ChartCard>
              <ChartCard title="Resume processing results">
                <SimplePie rows={Object.entries(data.resume_processing).map(([status, count]) => ({ status, count }))} nameKey="status" valueKey="count" />
              </ChartCard>
            </div>
          </>
        )}
      </Loadable>
    </>
  )
}

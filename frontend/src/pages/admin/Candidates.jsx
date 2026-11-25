import { useState } from 'react'
import { Link } from 'react-router-dom'
import useFetch from '../../hooks/useFetch'
import { Loadable, PageHeader, EmptyState, SkillChips } from '../../components/ui'

export default function Candidates() {
  const [filters, setFilters] = useState({ search: '', skill: '', location: '', min_experience: '', job_id: '' })
  const [applied, setApplied] = useState({})
  const jobs = useFetch('/api/jobs')
  const { data, loading, error, reload } = useFetch('/api/candidates', applied)
  const set = (field) => (event) => setFilters({ ...filters, [field]: event.target.value })

  function applyFilters(event) {
    event.preventDefault()
    // send only the filters that have a value; sorting by score needs a job
    const clean = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== ''))
    if (clean.job_id) clean.sort_by_score = true
    setApplied(clean)
  }

  return (
    <>
      <PageHeader title="Candidates" subtitle="Search, filter and open candidate profiles" />
      <form onSubmit={applyFilters} className="card mb-4 grid gap-3 md:grid-cols-6">
        <input className="input md:col-span-2" placeholder="Search name or email" value={filters.search} onChange={set('search')} />
        <input className="input" placeholder="Skill (e.g. python)" value={filters.skill} onChange={set('skill')} />
        <input className="input" placeholder="Location" value={filters.location} onChange={set('location')} />
        <input className="input" type="number" min="0" placeholder="Min. years exp." value={filters.min_experience} onChange={set('min_experience')} />
        <select className="input" value={filters.job_id} onChange={set('job_id')}>
          <option value="">Sort by match score for...</option>
          {jobs.data?.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
        </select>
        <button className="btn-primary md:col-span-6 md:w-40">Apply filters</button>
      </form>

      <Loadable loading={loading} error={error} reload={reload}>
        <div className="card overflow-x-auto p-0">
          {data?.length ? (
            <table className="w-full">
              <thead><tr><th className="th">Name</th><th className="th">Skills</th><th className="th">Experience</th><th className="th">Location</th><th className="th">Match score</th></tr></thead>
              <tbody>
                {data.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="td"><Link className="font-medium text-brand-600" to={`/admin/candidates/${c.id}${applied.job_id ? `?job=${applied.job_id}` : ''}`}>{c.name || c.email}</Link><div className="text-xs text-slate-400">{c.email}</div></td>
                    <td className="td max-w-xs"><SkillChips skills={(c.technical_skills || []).slice(0, 5)} /></td>
                    <td className="td">{c.total_experience_years || 0} yrs</td>
                    <td className="td">{c.location || '-'}</td>
                    <td className="td">{c.match_score ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <EmptyState title="No candidates found" hint="Upload resumes in Bulk Upload or change the filters." />}
        </div>
      </Loadable>
    </>
  )
}

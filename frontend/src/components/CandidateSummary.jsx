// Read-only view of a candidate profile (admin, interviewer and candidate use it).
import { SkillChips } from './ui'

function Section({ title, children }) {
  return <div className="mb-4"><p className="label">{title}</p>{children}</div>
}

export default function CandidateSummary({ candidate }) {
  return (
    <div>
      <div className="mb-4">
        <h2 className="text-xl font-bold text-navy-900">{candidate.name || 'Unnamed candidate'}</h2>
        <p className="text-sm text-slate-500">{[candidate.email, candidate.phone, candidate.location].filter(Boolean).join('  |  ')}</p>
        <p className="text-sm text-slate-500">{candidate.total_experience_years || 0} years of experience</p>
      </div>
      {candidate.summary && <Section title="Summary"><p className="text-sm">{candidate.summary}</p></Section>}
      <Section title="Technical skills"><SkillChips skills={candidate.technical_skills} /></Section>
      <Section title="Soft skills"><SkillChips skills={candidate.soft_skills} /></Section>
      <Section title="Education">
        {candidate.education?.length ? candidate.education.map((e, i) => <p key={i} className="text-sm">{[e.degree, e.institution, e.year].filter(Boolean).join(', ')}</p>) : <span className="text-sm text-slate-400">None</span>}
      </Section>
      <Section title="Employment history">
        {candidate.employment_history?.length ? candidate.employment_history.map((j, i) => (
          <div key={i} className="mb-1 text-sm"><b>{j.title}</b> at {j.company} <span className="text-slate-400">({j.start || '?'} - {j.end || '?'})</span>{j.description && <p className="text-slate-600">{j.description}</p>}</div>
        )) : <span className="text-sm text-slate-400">None</span>}
      </Section>
      <Section title="Projects">
        {candidate.projects?.length ? candidate.projects.map((p, i) => <div key={i} className="mb-1 text-sm"><b>{p.name}</b>{p.description && <span className="text-slate-600"> - {p.description}</span>}</div>) : <span className="text-sm text-slate-400">None</span>}
      </Section>
      <Section title="Certifications"><SkillChips skills={candidate.certifications} /></Section>
    </div>
  )
}

// Shows ONE candidate's AI match: score, component bars, matched/missing skills, explanation,
// and the human override control (AI recommends, admin decides).
import { useState } from 'react'
import api, { errorMessage } from '../services/api'
import { useToast } from '../context/ToastContext'
import { ScoreBar, SkillChips, StatusBadge } from './ui'

const OVERRIDE_CHOICES = ['Strong Match', 'Possible Match', 'Weak Match', 'Not a Match']
const COMPONENTS = [['skills', 'Required skills'], ['experience', 'Experience'], ['education', 'Education'], ['preferred', 'Preferred skills'], ['semantic', 'Semantic similarity']]

export default function MatchPanel({ match, onChanged }) {
  const toast = useToast()
  const [decision, setDecision] = useState(match.admin_override || '')
  const [reason, setReason] = useState(match.override_reason || '')
  const d = match.details

  async function saveOverride() {
    try {
      await api.put(`/api/matching/${match.match_id}/override`, { decision, reason })
      toast.success('Your decision was saved')
      onChanged?.()
    } catch (error) {
      toast.error(errorMessage(error))
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="flex h-20 w-20 flex-col items-center justify-center rounded-2xl bg-brand-50 text-brand-700">
          <span className="text-2xl font-bold">{match.final_score}%</span><span className="text-[10px]">required skills</span>
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm">AI recommendation: <StatusBadge value={match.ai_recommendation} /></div>
          {match.admin_override && <div className="flex items-center gap-2 text-sm">Admin decision: <StatusBadge value={match.admin_override} /></div>}
        </div>
      </div>

      <div>
        <p className="label">{d.scores.skills == null ? 'Weighted match breakdown' : 'Additional fit signals'}</p>
        {COMPONENTS.map(([key, label]) => (
          <ScoreBar key={key} label={label} score={d.scores[key]} weight={d.scores.skills == null ? d.weights[key] : undefined} />
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div><p className="label">Matched required skills</p><SkillChips skills={d.matched_skills} tone="green" /></div>
        <div><p className="label">Missing required skills</p><SkillChips skills={d.missing_skills} tone="red" /></div>
        <div><p className="label">Preferred skills matched</p><SkillChips skills={d.preferred_matched} tone="green" /></div>
        <div>
          <p className="label">Experience comparison</p>
          <p className="text-sm">Candidate: <b>{d.candidate_experience_years} yrs</b> &nbsp;|&nbsp; Job: <b>{d.job_min_experience}{d.job_max_experience != null ? `-${d.job_max_experience}` : '+'} yrs</b></p>
        </div>
      </div>

      <div className="rounded-lg bg-slate-50 p-3 text-sm">
        <p className="label">Why this score (generated from real data, not by an LLM)</p>
        {d.explanation || 'No explanation available.'}
      </div>

      <div className="rounded-lg border border-slate-200 p-3">
        <p className="label">Override the AI recommendation</p>
        <div className="flex flex-wrap gap-2">
          <select className="input max-w-[200px]" value={decision} onChange={(e) => setDecision(e.target.value)}>
            <option value="">Choose decision...</option>
            {OVERRIDE_CHOICES.map((c) => <option key={c}>{c}</option>)}
          </select>
          <input className="input flex-1" placeholder="Reason (optional)" value={reason} onChange={(e) => setReason(e.target.value)} />
          <button className="btn-secondary" disabled={!decision} onClick={saveOverride}>Save decision</button>
        </div>
      </div>
    </div>
  )
}

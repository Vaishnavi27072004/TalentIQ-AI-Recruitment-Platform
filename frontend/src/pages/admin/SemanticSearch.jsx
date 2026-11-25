import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search } from 'lucide-react'
import api, { errorMessage } from '../../services/api'
import { useToast } from '../../context/ToastContext'
import { PageHeader, EmptyState, Spinner, SkillChips } from '../../components/ui'

const EXAMPLES = ['Find Python developers with machine learning experience', 'Find candidates with SQL and Power BI skills', 'Find candidates who have worked on NLP projects', 'Find candidates suitable for a Data Analyst role']

export default function SemanticSearch() {
  const toast = useToast()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [busy, setBusy] = useState(false)

  async function search(text) {
    setBusy(true)
    try {
      const { data } = await api.post('/api/search/candidates', { query: text, top_k: 10 })
      setResults(data)
    } catch (error) { toast.error(errorMessage(error)) } finally { setBusy(false) }
  }

  return (
    <>
      <PageHeader title="Semantic Search" subtitle="Searches by meaning using embeddings + ChromaDB, not by keywords" />
      <form className="card mb-4" onSubmit={(e) => { e.preventDefault(); search(query) }}>
        <div className="flex gap-2">
          <input className="input" placeholder="Describe who you are looking for..." value={query} onChange={(e) => setQuery(e.target.value)} />
          <button className="btn-primary" disabled={busy || query.trim().length < 2}><Search size={16} />Search</button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLES.map((example) => <button type="button" key={example} className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600 hover:bg-brand-50" onClick={() => { setQuery(example); search(example) }}>{example}</button>)}
        </div>
      </form>

      {busy && <Spinner label="Searching..." />}
      {results && !busy && (results.length ? (
        <div className="space-y-3">
          {results.map((c, index) => (
            <div key={c.id} className="card flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs text-slate-400">#{index + 1}</p>
                <Link to={`/admin/candidates/${c.id}`} className="font-semibold text-brand-600">{c.name || c.email}</Link>
                <p className="text-xs text-slate-500">{c.total_experience_years || 0} yrs | {c.location || 'location not given'}</p>
                <div className="mt-2"><SkillChips skills={(c.technical_skills || []).slice(0, 8)} /></div>
                {c.summary && <p className="mt-2 max-w-2xl text-sm text-slate-600">{c.summary}</p>}
              </div>
              <div className="text-right"><p className="text-xl font-bold text-navy-900">{(c.similarity * 100).toFixed(0)}%</p><p className="text-xs text-slate-400">semantic similarity</p></div>
            </div>
          ))}
        </div>
      ) : <EmptyState title="No candidates indexed yet" hint="Upload resumes so they can be searched." />)}
    </>
  )
}

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { UploadCloud } from 'lucide-react'
import api, { errorMessage } from '../../services/api'
import { useToast } from '../../context/ToastContext'
import { PageHeader, StatusBadge } from '../../components/ui'

export default function BulkUpload() {
  const toast = useToast()
  const [files, setFiles] = useState([])
  const [results, setResults] = useState([])
  const [busy, setBusy] = useState(false)

  async function handleUpload() {
    setBusy(true)
    // Show every selected file as "processing" until the server answers.
    setResults(files.map((f) => ({ filename: f.name, status: 'processing' })))
    try {
      const form = new FormData()
      files.forEach((file) => form.append('files', file))
      const { data } = await api.post('/api/candidates/bulk-upload', form, { timeout: 600000 })
      setResults(data)
      const done = data.filter((r) => r.status === 'completed').length
      toast.success(`${done} of ${data.length} resumes processed`)
    } catch (error) {
      toast.error(errorMessage(error))
      setResults(files.map((f) => ({ filename: f.name, status: 'failed', error: 'Upload failed' })))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader title="Bulk Resume Upload" subtitle="Each resume is parsed by the LLM on its own. One bad file never stops the others." />
      <div className="card mb-4">
        <label className="flex cursor-pointer flex-col items-center rounded-xl border-2 border-dashed border-slate-300 p-8 text-slate-500 hover:border-brand-500">
          <UploadCloud size={32} />
          <span className="mt-2 text-sm">Click to choose PDF / DOCX resumes (max 5 MB each)</span>
          <input type="file" multiple className="hidden" accept=".pdf,.docx" onChange={(e) => { setFiles([...e.target.files]); setResults([]) }} />
        </label>
        {files.length > 0 && (
          <div className="mt-3 flex items-center justify-between">
            <span className="text-sm text-slate-600">{files.length} file(s) selected</span>
            <button className="btn-primary" disabled={busy} onClick={handleUpload}>{busy ? 'Processing...' : 'Upload & parse'}</button>
          </div>
        )}
      </div>

      {results.length > 0 && (
        <div className="card overflow-x-auto p-0">
          <table className="w-full">
            <thead><tr><th className="th">File</th><th className="th">Status</th><th className="th">Details</th></tr></thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={i}>
                  <td className="td">{r.filename}</td>
                  <td className="td"><StatusBadge value={r.status} /></td>
                  <td className="td text-slate-600">
                    {r.status === 'completed' && r.candidate_id ? <Link className="text-brand-600" to={`/admin/candidates/${r.candidate_id}`}>Open profile</Link> : r.error}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

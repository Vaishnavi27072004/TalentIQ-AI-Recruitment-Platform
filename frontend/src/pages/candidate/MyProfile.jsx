import { useState } from 'react'
import { UploadCloud, Download } from 'lucide-react'
import api, { downloadFile, errorMessage } from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { useToast } from '../../context/ToastContext'
import { Loadable, PageHeader } from '../../components/ui'
import CandidateEditor from '../../components/CandidateEditor'

export default function MyProfile() {
  const toast = useToast()
  const { data, loading, error, reload } = useFetch('/api/candidates/me')
  const [uploading, setUploading] = useState(false)
  const [editorKey, setEditorKey] = useState(0) // changing the key re-creates the form with fresh extracted data

  async function handleUpload(event) {
    const file = event.target.files[0]
    if (!file) return
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      await api.post('/api/candidates/me/resume', form, { timeout: 120000 })
      toast.success('Resume processed. Please review the extracted details below.')
      await reload()
      setEditorKey((k) => k + 1)
    } catch (err) { toast.error(errorMessage(err)) } finally { setUploading(false); event.target.value = '' }
  }

  return (
    <>
      <PageHeader title="My profile & resume" subtitle="Upload a PDF or DOCX to extract profile details. Review and correct them before saving." />
      <Loadable loading={loading} error={error} reload={reload}>
        {data && (
          <>
            <div className="card mb-4">
              <label className="flex cursor-pointer flex-col items-center rounded-xl border-2 border-dashed border-slate-300 p-6 text-slate-500 hover:border-brand-500">
                <UploadCloud size={28} />
                <span className="mt-2 text-sm">{uploading ? 'Extracting resume details...' : 'Click to upload resume (PDF or DOCX, max 5 MB)'}</span>
                <input type="file" className="hidden" accept=".pdf,.docx" disabled={uploading} onChange={handleUpload} />
              </label>
              {data.resumes.filter((r) => r.status === 'completed').map((r) => (
                <button key={r.id} className="btn-secondary mt-3 mr-2" onClick={() => downloadFile(`/api/candidates/resumes/${r.id}/download`, r.filename)}><Download size={15} />{r.filename}</button>
              ))}
            </div>
            <div className="card"><h3 className="mb-3 font-semibold text-navy-900">Extracted information (editable)</h3>
              <CandidateEditor key={editorKey} candidate={data} saveUrl="/api/candidates/me" onSaved={reload} />
            </div>
          </>
        )}
      </Loadable>
    </>
  )
}

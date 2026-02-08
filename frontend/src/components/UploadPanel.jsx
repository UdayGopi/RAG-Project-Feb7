import { useState, useEffect } from 'react'
import { tenants, upload } from '../api'

const steps = [
  { n: 1, title: 'Choose Tenant:', desc: 'Select an existing project/topic or create a new one to keep documents organized.' },
  { n: 2, title: 'Add Content:', desc: 'Paste a URL to ingest a webpage or upload one or more document files.' },
  { n: 3, title: 'Start Ingestion:', desc: 'Click "Upload & Ingest" to process and add content to the knowledge base.' },
  { n: 4, title: 'Start Chatting:', desc: 'Navigate to the Chat tab to ask questions about the newly added information.' },
]

export default function UploadPanel() {
  const [tenantList, setTenantList] = useState([])
  const [tenantId, setTenantId] = useState('')
  const [newTenantId, setNewTenantId] = useState('')
  const [url, setUrl] = useState('')
  const [files, setFiles] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [summary, setSummary] = useState(null)
  const [drag, setDrag] = useState(false)

  const loadTenants = async () => {
    try {
      const data = await tenants()
      setTenantList(data.tenants || [])
    } catch (_) {}
  }

  useEffect(() => {
    loadTenants()
  }, [])

  const onFileChange = (e) => {
    const list = e.target.files ? Array.from(e.target.files) : []
    setFiles(list)
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDrag(false)
    if (e.dataTransfer.files) setFiles(Array.from(e.dataTransfer.files))
  }

  const onSubmit = async (e) => {
    e.preventDefault()
    if (!tenantId && !newTenantId.trim()) {
      setSummary({ error: 'Please select or create a tenant.' })
      return
    }
    setSubmitting(true)
    setSummary(null)
    try {
      const formData = new FormData()
      if (tenantId) formData.append('tenant_id', tenantId)
      if (newTenantId.trim()) formData.append('new_tenant_id', newTenantId.trim())
      if (url.trim()) formData.append('url', url.trim())
      files.forEach((f) => formData.append('files', f))
      const result = await upload(formData)
      setSummary({
        message: result.message || 'Ingestion complete!',
        details: result.details,
        errors: result.errors,
      })
      setUrl('')
      setFiles([])
      setNewTenantId('')
      setTenantId('')
      loadTenants()
    } catch (err) {
      setSummary({ error: err.message })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="p-6 space-y-6 h-full overflow-y-auto bg-slate-50">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h3 className="text-xl font-bold text-slate-900 mb-4 tracking-tight">Ingest New Documents</h3>
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label htmlFor="tenant-select" className="block text-sm font-semibold text-slate-700 mb-2">Select Existing Tenant</label>
              <select
                id="tenant-select"
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
                className="w-full p-3 border border-slate-300 rounded-lg bg-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">-- Select --</option>
                {tenantList.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div className="text-center py-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Or</span>
            </div>
            <div>
              <label htmlFor="new-tenant-input" className="block text-sm font-semibold text-slate-700 mb-2">Create New Tenant</label>
              <input
                id="new-tenant-input"
                type="text"
                value={newTenantId}
                onChange={(e) => setNewTenantId(e.target.value)}
                placeholder="Enter new tenant name..."
                className="w-full p-3 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <hr className="border-slate-200" />
            <div>
              <label htmlFor="url-input" className="block text-sm font-semibold text-slate-700 mb-2">Ingest from URL</label>
              <input
                id="url-input"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/policy"
                className="w-full p-3 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Upload Files</label>
              <div
                onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
                onDragLeave={(e) => { e.preventDefault(); setDrag(false) }}
                onDrop={onDrop}
                className={`mt-2 flex justify-center items-center flex-col w-full h-32 px-6 transition bg-white border-2 border-slate-300 border-dashed rounded-xl cursor-pointer hover:border-blue-400 hover:bg-blue-50 ${drag ? 'border-blue-500 bg-blue-50' : ''}`}
              >
                <input
                  type="file"
                  id="file-input"
                  multiple
                  className="hidden"
                  onChange={onFileChange}
                />
                <label htmlFor="file-input" className="text-center cursor-pointer">
                  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mx-auto text-slate-400 mb-2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  <span className="font-semibold text-slate-700 text-sm block mb-1">Drag & drop or click to select</span>
                  <span className="text-xs text-slate-500">PDF, TXT, DOCX supported</span>
                </label>
              </div>
            </div>
            {files.length > 0 && (
              <ul className="list-disc pl-5 text-slate-700 space-y-1 text-sm">
                {files.map((f, i) => (
                  <li key={i}>{f.name}</li>
                ))}
              </ul>
            )}
            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-blue-600 text-white font-semibold p-3 rounded-xl hover:bg-blue-700 transition-all shadow-md hover:shadow-lg disabled:opacity-70"
            >
              {submitting ? 'Ingesting...' : 'Upload & Ingest'}
            </button>
          </form>
          {summary && (
            <div className="mt-4 text-sm bg-slate-50 border border-slate-200 rounded-xl p-4">
              {summary.error && <p className="text-red-700 font-medium">{summary.error}</p>}
              {summary.message && <p><strong className="text-slate-900">Status:</strong> <span className="text-slate-700">{summary.message}</span></p>}
              {summary.details && summary.details.length > 0 && (
                <>
                  <p className="mt-2"><strong className="text-slate-900">Details:</strong></p>
                  <ul className="mt-1 space-y-1 text-slate-700">{summary.details.map((d, i) => <li key={i}>{d}</li>)}</ul>
                </>
              )}
              {summary.errors && summary.errors.length > 0 && (
                <>
                  <p className="mt-2 text-red-600 font-medium">Errors:</p>
                  <ul className="mt-1 space-y-1 text-red-700">{summary.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
                </>
              )}
            </div>
          )}
        </div>

        <div className="bg-gradient-to-br from-blue-50 to-white rounded-xl border border-blue-200 p-6 shadow-sm">
          <h4 className="font-bold text-slate-900 text-lg mb-4 tracking-tight">How to Ingest Content</h4>
          <ul className="space-y-4 text-sm text-slate-600">
            {steps.map((s) => (
              <li key={s.n} className="flex gap-3">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold">{s.n}</div>
                <div>
                  <strong className="text-slate-900">{s.title}</strong> {s.desc}
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}

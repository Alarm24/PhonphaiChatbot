import { useEffect, useState, useRef, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Trash2, Upload, RefreshCw } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import {
  listFiles,
  uploadFile,
  deleteFile,
  type FileItem,
  type FileTheme,
} from '../services/api'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Input } from '../components/ui/input'

const THEMES: { value: FileTheme; label: string }[] = [
  { value: 'remedy', label: 'Remedy (เคสร้องเรียน)' },
  { value: 'disaster', label: 'Disaster (ภัยพิบัติ)' },
  { value: 'manual', label: 'Manual (คู่มือ)' },
]

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(iso: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString()
}

export function AdminFilesPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [files, setFiles] = useState<FileItem[]>([])
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState<string>('')

  const [theme, setTheme] = useState<FileTheme>('manual')
  const [picked, setPicked] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    if (user === null) {
      navigate('/login')
    }
  }, [user, navigate])

  const refresh = async () => {
    setLoading(true)
    setListError('')
    try {
      const data = await listFiles()
      setFiles(data)
    } catch (err) {
      setListError(err instanceof Error ? err.message : 'ไม่สามารถโหลดรายการไฟล์ได้')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (user?.role === 'admin') {
      void refresh()
    }
  }, [user?.role])

  if (!user) {
    return null
  }

  if (user.role !== 'admin') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md p-8 text-center">
          <h1 className="text-xl font-semibold text-gray-900 mb-2">403 — Forbidden</h1>
          <p className="text-sm text-gray-600 mb-6">
            หน้านี้สำหรับผู้ดูแลระบบเท่านั้น
          </p>
          <Link to="/" className="text-sm text-[#D32F2F] underline">
            กลับสู่หน้าแชท
          </Link>
        </Card>
      </div>
    )
  }

  const handleUpload = async (e: FormEvent) => {
    e.preventDefault()
    if (!picked) {
      setUploadMsg({ kind: 'err', text: 'กรุณาเลือกไฟล์ก่อน' })
      return
    }
    setUploading(true)
    setUploadMsg(null)
    try {
      const result = await uploadFile(picked, theme)
      setUploadMsg({ kind: 'ok', text: result.message || 'อัปโหลดสำเร็จ' })
      setPicked(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      await refresh()
    } catch (err) {
      setUploadMsg({
        kind: 'err',
        text: err instanceof Error ? err.message : 'อัปโหลดไม่สำเร็จ',
      })
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (f: FileItem) => {
    const ok = window.confirm(`ลบไฟล์ "${f.file_name}" ใช่หรือไม่?`)
    if (!ok) return
    setDeletingId(f.file_id)
    try {
      await deleteFile(f.file_id, f.file_name, f.theme)
      await refresh()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'ลบไม่สำเร็จ')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate('/')}
              aria-label="Back to chat"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-xl text-gray-900">จัดการข้อมูล / Manage Data</h1>
              <p className="text-sm text-gray-600">
                อัปโหลด ลบ และดูรายการไฟล์ในฐานข้อมูล
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-700">{user.username}</span>
            <span className="rounded bg-[#D32F2F] px-1.5 py-0.5 text-[10px] font-semibold uppercase text-white">
              admin
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-6 space-y-6">
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">อัปโหลดไฟล์ใหม่</h2>
          <form onSubmit={handleUpload} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-1">
                <label className="text-sm text-gray-700">ไฟล์</label>
                <Input
                  ref={fileInputRef}
                  type="file"
                  onChange={(e) => {
                    setPicked(e.target.files?.[0] ?? null)
                    setUploadMsg(null)
                  }}
                  disabled={uploading}
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm text-gray-700">หมวดหมู่ / Theme</label>
                <select
                  value={theme}
                  onChange={(e) => setTheme(e.target.value as FileTheme)}
                  disabled={uploading}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {THEMES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {uploadMsg && (
              <p
                className={`text-sm ${
                  uploadMsg.kind === 'ok' ? 'text-green-700' : 'text-red-600'
                }`}
              >
                {uploadMsg.text}
              </p>
            )}

            <Button
              type="submit"
              disabled={uploading || !picked}
              className="bg-[#D32F2F] hover:bg-red-700 text-white"
            >
              <Upload className="w-4 h-4 mr-2" />
              {uploading ? 'กำลังอัปโหลด...' : 'อัปโหลด'}
            </Button>
          </form>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">รายการไฟล์ทั้งหมด</h2>
            <Button
              variant="outline"
              size="sm"
              onClick={refresh}
              disabled={loading}
              aria-label="Refresh"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              รีเฟรช
            </Button>
          </div>

          {listError && <p className="text-sm text-red-600 mb-4">{listError}</p>}

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-gray-600">
                  <th className="py-2 pr-4 font-medium">ชื่อไฟล์</th>
                  <th className="py-2 pr-4 font-medium">หมวด</th>
                  <th className="py-2 pr-4 font-medium">ขนาด</th>
                  <th className="py-2 pr-4 font-medium">อัปโหลดเมื่อ</th>
                  <th className="py-2 pr-2 font-medium text-right">การกระทำ</th>
                </tr>
              </thead>
              <tbody>
                {loading && files.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-gray-500">
                      กำลังโหลด...
                    </td>
                  </tr>
                ) : files.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-gray-500">
                      ยังไม่มีไฟล์ในระบบ
                    </td>
                  </tr>
                ) : (
                  files.map((f) => (
                    <tr key={f.file_id} className="border-b border-gray-100">
                      <td className="py-2 pr-4 text-gray-900 break-all">{f.file_name}</td>
                      <td className="py-2 pr-4 text-gray-700">{f.theme}</td>
                      <td className="py-2 pr-4 text-gray-700">{formatSize(f.size_bytes)}</td>
                      <td className="py-2 pr-4 text-gray-700">{formatDate(f.created_at)}</td>
                      <td className="py-2 pr-2 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(f)}
                          disabled={deletingId === f.file_id}
                          className="text-[#D32F2F] hover:bg-red-50"
                        >
                          <Trash2 className="w-4 h-4 mr-1" />
                          {deletingId === f.file_id ? 'กำลังลบ...' : 'ลบ'}
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </main>
    </div>
  )
}

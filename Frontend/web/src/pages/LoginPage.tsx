import { useState, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) {
      setError('กรุณากรอกชื่อผู้ใช้และรหัสผ่าน')
      return
    }
    login(username.trim())
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-lg overflow-hidden">
        {/* Header */}
        <div className="bg-[#D32F2F] px-8 py-10 text-center">
          <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-[#D32F2F] font-bold text-2xl">P</span>
          </div>
          <h1 className="text-white text-2xl font-semibold">พนไผ่</h1>
          <p className="text-red-200 text-sm mt-1">ระบบ AI สนับสนุนการจัดการภัยพิบัติ</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-8 py-8 space-y-4">
          <div className="space-y-1">
            <label className="text-sm text-gray-700">ชื่อผู้ใช้</label>
            <Input
              value={username}
              onChange={(e) => { setUsername(e.target.value); setError('') }}
              placeholder="กรอกชื่อผู้ใช้"
              autoComplete="username"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm text-gray-700">รหัสผ่าน</label>
            <Input
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError('') }}
              placeholder="กรอกรหัสผ่าน"
              autoComplete="current-password"
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <Button
            type="submit"
            className="w-full bg-[#D32F2F] hover:bg-red-700 text-white mt-2"
          >
            เข้าสู่ระบบ
          </Button>

          <div className="text-center">
            <Link to="/" className="text-sm text-gray-500 hover:text-gray-700 underline">
              ข้ามขั้นตอนนี้ / ใช้งานโดยไม่เข้าสู่ระบบ
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}

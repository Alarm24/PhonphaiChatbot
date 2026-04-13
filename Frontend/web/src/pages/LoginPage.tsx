import { useState, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'

export function LoginPage() {
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [mode, setMode] = useState<'login' | 'register'>('login')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password.trim()) {
      setError('กรุณากรอกอีเมลและรหัสผ่าน')
      return
    }

    setIsLoading(true)
    setError('')

    try {
      if (mode === 'register') {
        await register(email.trim(), password)
      } else {
        await login(email.trim(), password)
      }
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'เกิดข้อผิดพลาด')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-lg overflow-hidden">
        <form onSubmit={handleSubmit} className="px-8 py-8 space-y-4">
          <h2 className="text-lg font-semibold text-center text-gray-800">
            {mode === 'login' ? 'เข้าสู่ระบบ' : 'ลงทะเบียน'}
          </h2>

          <div className="space-y-1">
            <label className="text-sm text-gray-700">อีเมล</label>
            <Input
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setError('') }}
              placeholder="กรอกอีเมล"
              autoComplete="email"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm text-gray-700">รหัสผ่าน</label>
            <Input
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError('') }}
              placeholder="กรอกรหัสผ่าน"
              autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
            />
            {mode === 'register' && (
              <p className="text-xs text-gray-500">อย่างน้อย 8 ตัวอักษร มีตัวอักษรและตัวเลข</p>
            )}
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <Button
            type="submit"
            disabled={isLoading}
            className="w-full bg-[#D32F2F] hover:bg-red-700 text-white mt-2"
          >
            {isLoading
              ? 'กำลังดำเนินการ...'
              : mode === 'login'
                ? 'เข้าสู่ระบบ'
                : 'ลงทะเบียน'}
          </Button>

          <div className="text-center space-y-2">
            <button
              type="button"
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
              className="text-sm text-[#D32F2F] hover:text-red-700 underline"
            >
              {mode === 'login' ? 'ยังไม่มีบัญชี? ลงทะเบียน' : 'มีบัญชีแล้ว? เข้าสู่ระบบ'}
            </button>
            <div>
              <Link to="/" className="text-sm text-gray-500 hover:text-gray-700 underline">
                ข้ามขั้นตอนนี้ / ใช้งานโดยไม่เข้าสู่ระบบ
              </Link>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}

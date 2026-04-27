import { useNavigate } from 'react-router-dom'
import { Lock } from 'lucide-react'
import { Button } from './ui/button'

interface LoginRequiredModalProps {
  open: boolean
  onClose: () => void
}

export function LoginRequiredModal({ open, onClose }: LoginRequiredModalProps) {
  const navigate = useNavigate()

  if (!open) return null

  const goLogin = () => {
    onClose()
    navigate('/login')
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex justify-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50">
            <Lock className="h-6 w-6 text-[#D32F2F]" />
          </div>
        </div>
        <h2 className="mb-2 text-center text-lg font-semibold text-gray-900">
          จำเป็นต้องเข้าสู่ระบบ
        </h2>
        <p className="mb-6 text-center text-sm text-gray-600">
          กรุณาเข้าสู่ระบบเพื่อสอบถามข้อมูลคำร้อง (หมายเลข SKN-XXXX-XXXX)
        </p>
        <div className="flex flex-col gap-2">
          <Button
            onClick={goLogin}
            className="w-full bg-[#D32F2F] text-white hover:bg-red-700"
          >
            เข้าสู่ระบบ
          </Button>
          <Button variant="ghost" onClick={onClose} className="w-full">
            ยกเลิก
          </Button>
        </div>
      </div>
    </div>
  )
}

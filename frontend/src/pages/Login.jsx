import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'
import Button from '../components/ui/Button.jsx'
import Input from '../components/ui/Input.jsx'

export default function Login() {
  const navigate = useNavigate()
  const { login, isLoading } = useAuth()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!form.email || !form.password) {
      setError('Preencha e-mail e senha.')
      return
    }

    try {
      await login(form.email, form.password)
      navigate('/dashboard', { replace: true })
    } catch {
      setError('E-mail ou senha inválidos. Verifique suas credenciais.')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 dark:from-navy-950 dark:to-navy-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary-600 dark:bg-violet-600 mb-4">
            <span className="text-3xl font-bold text-white">U</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">UidCore</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">Acesse sua conta para continuar</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 dark:bg-navy-800 dark:border-navy-600 dark:shadow-none">
          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            <Input
              label="E-mail"
              id="email"
              name="email"
              type="email"
              placeholder="seu@email.com"
              value={form.email}
              onChange={handleChange}
              autoComplete="email"
              autoFocus
            />
            <Input
              label="Senha"
              id="password"
              name="password"
              type="password"
              placeholder="••••••••"
              value={form.password}
              onChange={handleChange}
              autoComplete="current-password"
            />

            {error && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 dark:bg-red-950/40 dark:border-red-800">
                <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
              </div>
            )}

            <Button type="submit" className="w-full" loading={isLoading} size="lg">
              Entrar
            </Button>
          </form>
        </div>

        <p className="text-center text-xs text-gray-400 dark:text-slate-500 mt-6">
          UidCore &copy; {new Date().getFullYear()} — Uid Software
        </p>
      </div>
    </div>
  )
}

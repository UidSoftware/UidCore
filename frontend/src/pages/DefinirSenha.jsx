import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import api from '../api/client.js'
import { extractErrorMessage } from '../utils/errors.js'
import Button from '../components/ui/Button.jsx'
import Input from '../components/ui/Input.jsx'

export default function DefinirSenha() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const uid = params.get('uid') || ''
  const token = params.get('token') || ''

  const [senha, setSenha] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [erro, setErro] = useState('')
  const [sucesso, setSucesso] = useState(false)
  const [carregando, setCarregando] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErro('')

    if (senha.length < 6) {
      setErro('A senha deve ter pelo menos 6 caracteres.')
      return
    }
    if (senha !== confirmar) {
      setErro('As senhas não coincidem.')
      return
    }

    setCarregando(true)
    try {
      await api.post('/accounts/definir-senha/', { uid, token, senha })
      setSucesso(true)
    } catch (error) {
      setErro(error?.response?.data?.erro || extractErrorMessage(error, 'Link inválido ou expirado. Solicite um novo email de acesso.'))
    } finally {
      setCarregando(false)
    }
  }

  if (!uid || !token) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 dark:from-navy-950 dark:to-navy-900 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 dark:bg-navy-800 dark:border-navy-600 dark:shadow-none max-w-sm text-center">
          <p className="text-sm text-red-600 dark:text-red-400">
            Link inválido. Solicite um novo email de acesso ao administrador.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 dark:from-navy-950 dark:to-navy-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary-600 dark:bg-violet-600 mb-4">
            <span className="text-3xl font-bold text-white">U</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">UidCore</h1>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 dark:bg-navy-800 dark:border-navy-600 dark:shadow-none">
          {sucesso ? (
            <div className="text-center space-y-4">
              <div className="text-4xl">✅</div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-slate-100">Senha definida!</h2>
              <p className="text-sm text-gray-500 dark:text-slate-400">Sua senha foi criada com sucesso.</p>
              <Button onClick={() => navigate('/login')} className="w-full" size="lg">
                Fazer login
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              <div className="text-center mb-2">
                <h2 className="text-xl font-bold text-gray-900 dark:text-slate-100">Defina sua senha</h2>
                <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">Mínimo 6 caracteres</p>
              </div>

              {erro && (
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 dark:bg-red-950/40 dark:border-red-800">
                  <p className="text-sm text-red-700 dark:text-red-300">{erro}</p>
                </div>
              )}

              <Input
                label="Nova senha" type="password" autoComplete="new-password" autoFocus
                value={senha} onChange={(e) => setSenha(e.target.value)}
              />
              <Input
                label="Confirmar senha" type="password" autoComplete="new-password"
                value={confirmar} onChange={(e) => setConfirmar(e.target.value)}
              />

              <Button type="submit" className="w-full" loading={carregando} size="lg">
                Salvar senha
              </Button>
            </form>
          )}
        </div>

        <p className="text-center text-xs text-gray-400 dark:text-slate-500 mt-6">
          UidCore &copy; {new Date().getFullYear()} — Uid Software
        </p>
      </div>
    </div>
  )
}

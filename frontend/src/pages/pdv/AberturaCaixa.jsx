import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Unlock, User as UserIcon, Clock } from 'lucide-react'
import api from '../../api/client.js'
import { extractErrorMessage } from '../../utils/errors.js'
import Button from '../../components/ui/Button.jsx'
import useAuthStore from '../../stores/authStore.js'

/**
 * Tela 1 — Abertura de Caixa (RF-01 / RF-02)
 * Redireciona para /pdv se já houver sessão ABERTA.
 */
export default function AberturaCaixa() {
  const navigate = useNavigate()
  const location = useLocation()
  const user = useAuthStore((s) => s.user)

  // RF-21 — data/hora fixada no mount (tela é um gate rápido, não um dashboard)
  const [dataHoraAtual] = useState(() =>
    new Date().toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
  )

  const [contas, setContas] = useState([])
  const [conta, setConta] = useState('')
  const [valorAbertura, setValorAbertura] = useState('')
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [loadingContas, setLoadingContas] = useState(true)
  const [sessaoAtiva, setSessaoAtiva] = useState(null)
  const [toast, setToast] = useState(null)

  const mostrarToast = (msg, tipo = 'success') => {
    setToast({ msg, tipo })
    setTimeout(() => setToast(null), tipo === 'error' ? 7000 : 3500)
  }

  useEffect(() => {
    Promise.all([
      api.get('/pdv/sessoes/atual/').catch(() => null),
      api.get('/financeiro/contas/?tipo=CAIXA&page_size=100'),
    ]).then(([sessaoRes, contasRes]) => {
      if (sessaoRes?.data) {
        setSessaoAtiva(sessaoRes.data)
      }
      const lista = contasRes.data.results || contasRes.data || []
      setContas(lista)
    }).catch((err) => {
      mostrarToast(extractErrorMessage(err, 'Erro ao carregar dados.'), 'error')
    }).finally(() => setLoadingContas(false))
  }, [])

  // RF-23 — mensagem amigável vinda do redirecionamento de sessão encerrada
  // (FrenteDeCaixa navega pra aqui com state.mensagem em vez de exibir o
  // erro cru do backend)
  useEffect(() => {
    if (location.state?.mensagem) {
      mostrarToast(location.state.mensagem, 'error')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state])

  const validar = () => {
    const e = {}
    if (!conta) e.conta = 'Selecione uma conta.'
    if (!valorAbertura || parseFloat(valorAbertura) < 0) e.valorAbertura = 'Informe o valor de abertura.'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validar()) return
    setSaving(true)
    setErrors({})
    try {
      await api.post('/pdv/sessoes/', {
        conta: parseInt(conta),
        valor_abertura: valorAbertura,
      })
      navigate('/pdv')
    } catch (err) {
      const data = err?.response?.data
      if (data?.conta) {
        setErrors({ conta: Array.isArray(data.conta) ? data.conta[0] : data.conta })
      } else {
        mostrarToast(extractErrorMessage(err, 'Erro ao abrir caixa.'), 'error')
      }
    } finally {
      setSaving(false)
    }
  }

  if (loadingContas) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <p className="text-gray-400 text-sm">Carregando...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-8">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white ${
          toast.tipo === 'error' ? 'bg-red-600' : 'bg-accent-600'
        }`}>
          {toast.msg}
        </div>
      )}

      <div className="w-full max-w-md">
        {/* Aviso de sessão ativa em outra conta */}
        {sessaoAtiva && (
          <div className="mb-4 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-sm px-4 py-3">
            <p className="font-medium">Você já tem uma sessão aberta.</p>
            <p className="mt-1 text-blue-600">
              Conta: {sessaoAtiva.conta_nome || `#${sessaoAtiva.conta}`} · Aberta às{' '}
              {new Date(sessaoAtiva.data_abertura).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
            </p>
            <button
              type="button"
              onClick={() => navigate('/pdv')}
              className="mt-2 text-primary-600 text-sm font-medium hover:underline"
            >
              Ir para o caixa aberto
            </button>
          </div>
        )}

        {/* Card de abertura */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
          <div className="text-center mb-6">
            <Unlock size={32} className="mx-auto text-primary-600 mb-3" />
            <h1 className="text-xl font-bold text-gray-900">Abrir Caixa</h1>
            <p className="text-sm text-gray-500 mt-1">
              Selecione a conta e informe o valor de abertura
            </p>
          </div>

          {/* RF-21 — operador logado + data/hora atual */}
          <div className="flex items-center justify-center gap-4 text-xs text-gray-500 pb-4 mb-4 border-b border-gray-100">
            <span className="flex items-center gap-1 truncate max-w-[140px]">
              <UserIcon size={12} /> {user?.nome_completo || user?.email || 'Operador'}
            </span>
            <span className="flex items-center gap-1">
              <Clock size={12} /> {dataHoraAtual}
            </span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Conta */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Conta <span className="text-red-500">*</span>
              </label>
              <select
                value={conta}
                onChange={(e) => { setConta(e.target.value); setErrors((prev) => ({ ...prev, conta: undefined })) }}
                className={`w-full rounded-lg border px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors ${
                  errors.conta ? 'border-red-500 bg-red-50' : 'border-gray-300 bg-white'
                }`}
              >
                <option value="">Selecione...</option>
                {contas.map((c) => (
                  <option key={c.id} value={c.id}>{c.nome}</option>
                ))}
              </select>
              {errors.conta && <p className="mt-1 text-xs text-red-600">{errors.conta}</p>}
            </div>

            {/* Valor de abertura */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Valor de Abertura (Fundo de Troco) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={valorAbertura}
                onChange={(e) => setValorAbertura(e.target.value)}
                placeholder="0,00"
                className={`w-full rounded-lg border px-3 py-2 text-sm text-right font-mono focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors ${
                  errors.valorAbertura ? 'border-red-500 bg-red-50' : 'border-gray-300 bg-white'
                }`}
              />
              {errors.valorAbertura && <p className="mt-1 text-xs text-red-600">{errors.valorAbertura}</p>}
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={saving}
              className="w-full"
            >
              <Unlock size={18} className="mr-2" />
              Abrir Caixa
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}

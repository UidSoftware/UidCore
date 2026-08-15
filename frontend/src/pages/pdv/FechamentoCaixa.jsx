import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Lock, AlertTriangle, CheckCircle } from 'lucide-react'
import api from '../../api/client.js'
import { extractErrorMessage } from '../../utils/errors.js'
import Button from '../../components/ui/Button.jsx'
import Card from '../../components/ui/Card.jsx'
import ResumoSessao from './components/ResumoSessao.jsx'

const BRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

function formatarDataHora(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function FechamentoCaixa() {
  const navigate = useNavigate()

  const [sessao, setSessao] = useState(null)
  const [resumo, setResumo] = useState({})
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState(null)

  const [contagem, setContagem] = useState('')
  const [observacoes, setObservacoes] = useState('')
  const [fechando, setFechando] = useState(false)
  const [toast, setToast] = useState(null)

  const mostrarToast = (msg, tipo = 'success') => {
    setToast({ msg, tipo })
    setTimeout(() => setToast(null), tipo === 'error' ? 7000 : 3500)
  }

  useEffect(() => {
    api.get('/pdv/sessoes/atual/')
      .then((res) => {
        setSessao(res.data)
        setResumo(res.data.resumo || {})
      })
      .catch(() => {
        navigate('/pdv/abertura')
      })
      .finally(() => setLoading(false))
  }, [navigate])

  // Calcular diferença em tempo real
  const calculado = parseFloat(resumo?.valor_calculado_dinheiro ?? sessao?.valor_fechamento_calculado ?? 0)
  const contagemNum = contagem !== '' ? parseFloat(contagem) : null
  const diferenca = contagemNum !== null ? (calculado - contagemNum) : null
  const temDiferenca = diferenca !== null && Math.abs(diferenca) >= 0.01
  const diferencaGrande = diferenca !== null && Math.abs(diferenca) > calculado * 0.05

  const handleFechar = async () => {
    if (!sessao) return
    if (!window.confirm('Confirmar fechamento do caixa? Esta ação não pode ser desfeita.')) return

    setFechando(true)
    try {
      const payload = {
        observacoes: observacoes.trim(),
      }
      if (contagem !== '') {
        payload.valor_fechamento_informado = contagem
      }
      await api.post(`/pdv/sessoes/${sessao.id}/fechar/`, payload)
      mostrarToast('Caixa fechado com sucesso!')
      setTimeout(() => navigate('/pdv/abertura'), 1500)
    } catch (err) {
      mostrarToast(extractErrorMessage(err, 'Erro ao fechar caixa.'), 'error')
    } finally {
      setFechando(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <p className="text-gray-400 text-sm dark:text-slate-500">Carregando...</p>
      </div>
    )
  }

  if (erro) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 text-sm dark:text-red-400">{erro}</p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white ${
          toast.tipo === 'error' ? 'bg-red-600' : 'bg-accent-600'
        }`}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2 dark:text-slate-100">
          <Lock size={22} className="text-gray-700 dark:text-slate-300" />
          Fechar Caixa
          {sessao && <span className="text-gray-400 font-normal text-lg dark:text-slate-500">— Sessão #{sessao.id}</span>}
        </h1>
        {sessao && (
          <p className="text-sm text-gray-500 mt-1 dark:text-slate-400">
            {sessao.conta_nome || `Conta #${sessao.conta}`} · aberta em {formatarDataHora(sessao.data_abertura)}
          </p>
        )}
      </div>

      {/* Resumo da sessão */}
      <ResumoSessao sessao={sessao} resumo={resumo} />

      {/* Valor calculado */}
      <Card>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-700 dark:text-slate-300">Valor calculado em caixa (dinheiro físico)</span>
          <span className="text-lg font-bold text-gray-900 font-mono dark:text-slate-100">{BRL(calculado)}</span>
        </div>
        <p className="text-xs text-gray-400 mt-1 dark:text-slate-500">
          Abertura + Vendas em dinheiro − Sangrias + Suprimentos
        </p>
      </Card>

      {/* Contagem física */}
      <Card title="Conferência do caixa">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1 dark:text-slate-300">
              Contagem física (opcional)
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={contagem}
              onChange={(e) => setContagem(e.target.value)}
              placeholder="Digite o valor contado..."
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-right font-mono focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:focus:ring-violet-500"
            />
          </div>

          {/* Diferença em tempo real */}
          {contagemNum !== null && (
            <div className={`flex items-center justify-between p-3 rounded-lg ${
              !temDiferenca ? 'bg-green-50 dark:bg-emerald-950/40' : diferencaGrande ? 'bg-red-50 dark:bg-red-950/40' : 'bg-yellow-50 dark:bg-amber-950/40'
            }`}>
              <div className={`flex items-center gap-2 text-sm font-medium ${
                !temDiferenca ? 'text-green-700 dark:text-emerald-300' : diferencaGrande ? 'text-red-700 dark:text-red-300' : 'text-yellow-700 dark:text-amber-300'
              }`}>
                {!temDiferenca
                  ? <CheckCircle size={16} />
                  : <AlertTriangle size={16} />
                }
                Diferença
              </div>
              <span className={`font-mono font-bold ${
                !temDiferenca ? 'text-green-700 dark:text-emerald-300' : diferencaGrande ? 'text-red-700 dark:text-red-300' : 'text-yellow-700 dark:text-amber-300'
              }`}>
                {BRL(diferenca)}
              </span>
            </div>
          )}

          {/* RN-07: aviso explícito que diferença não bloqueia fechamento */}
          {temDiferenca && (
            <p className="text-xs text-gray-500 dark:text-slate-400">
              O fechamento será registrado mesmo com diferença — a diferença ficará documentada na sessão.
            </p>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1 dark:text-slate-300">
              Observações (opcional)
            </label>
            <textarea
              rows={2}
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
              placeholder="Anotações sobre o fechamento..."
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500"
            />
          </div>
        </div>
      </Card>

      {/* Botões */}
      <div className="flex justify-end gap-3">
        <Button
          type="button"
          variant="secondary"
          onClick={() => navigate('/pdv')}
          disabled={fechando}
        >
          Cancelar
        </Button>
        <Button
          type="button"
          variant="danger"
          loading={fechando}
          onClick={handleFechar}
        >
          <Lock size={16} className="mr-2" />
          Fechar Caixa
        </Button>
      </div>
    </div>
  )
}

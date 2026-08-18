import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, Calendar, ClipboardList } from 'lucide-react'
import api from '../../api/client.js'
import { extractErrorMessage } from '../../utils/errors.js'
import useAuthStore from '../../stores/authStore.js'
import Card from '../../components/ui/Card.jsx'
import Button from '../../components/ui/Button.jsx'
import Input from '../../components/ui/Input.jsx'
import Select from '../../components/ui/Select.jsx'
import Modal from '../../components/ui/Modal.jsx'
import Pagination from '../../components/ui/Pagination.jsx'

const PAGE_SIZE = 20

const STATUS_SESSAO_BADGES = {
  ABERTA: 'bg-yellow-100 text-yellow-800 dark:bg-amber-900/30 dark:text-amber-300',
  FECHADA: 'bg-blue-100 text-blue-800 dark:bg-blue-950/40 dark:text-blue-300',
}

const STATUS_OPTIONS = [
  { value: '', label: 'Todos os status' },
  { value: 'ABERTA', label: 'Aberta' },
  { value: 'FECHADA', label: 'Fechada' },
]

const BRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

function formatarDataHora(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function Badge({ status }) {
  return (
    <span
      className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
        STATUS_SESSAO_BADGES[status] || 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400'
      }`}
    >
      {status}
    </span>
  )
}

function DiferencaCell({ valor }) {
  const v = Number(valor || 0)
  if (v === 0) {
    return <span className="font-mono text-green-700 dark:text-emerald-400 font-semibold">{BRL(0)}</span>
  }
  return (
    <span className="font-mono text-red-700 dark:text-red-400 font-semibold flex items-center gap-1">
      <AlertTriangle size={14} className="text-red-600 dark:text-red-400 shrink-0" />
      {BRL(v)}
    </span>
  )
}

function ResumoSessaoModal({ sessao }) {
  const pagamentos = sessao.vendas_por_pagamento || sessao.totais_por_forma_pagamento || []
  const movimentos = sessao.movimentos || []

  const totalSangrias = movimentos
    .filter((m) => m.tipo === 'SANGRIA')
    .reduce((s, m) => s + Number(m.valor || 0), 0)

  const totalSuprimentos = movimentos
    .filter((m) => m.tipo === 'SUPRIMENTO')
    .reduce((s, m) => s + Number(m.valor || 0), 0)

  return (
    <div className="space-y-4">
      {/* Dados gerais */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gray-50 rounded-lg p-3 dark:bg-navy-900/50">
          <p className="text-xs text-gray-500 dark:text-slate-400">Conta</p>
          <p className="font-semibold text-gray-900 dark:text-slate-100 truncate">
            {sessao.conta?.nome || sessao.conta_nome || '—'}
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 dark:bg-navy-900/50">
          <p className="text-xs text-gray-500 dark:text-slate-400">Operador</p>
          <p className="font-semibold text-gray-900 dark:text-slate-100">
            {sessao.operador_nome || '—'}
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 dark:bg-navy-900/50">
          <p className="text-xs text-gray-500 dark:text-slate-400">Abertura</p>
          <p className="font-semibold text-gray-900 dark:text-slate-100">{formatarDataHora(sessao.data_abertura)}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 dark:bg-navy-900/50">
          <p className="text-xs text-gray-500 dark:text-slate-400">Fechamento</p>
          <p className="font-semibold text-gray-900 dark:text-slate-100">{formatarDataHora(sessao.data_fechamento)}</p>
        </div>
      </div>

      {/* KPIs financeiros */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-blue-50 rounded-xl p-3 dark:bg-blue-950/40">
          <p className="text-xs text-blue-700 dark:text-blue-300 opacity-80">Valor Abertura</p>
          <p className="font-bold text-blue-700 dark:text-blue-300 mt-1">{BRL(sessao.valor_abertura)}</p>
        </div>
        <div className="bg-green-50 rounded-xl p-3 dark:bg-emerald-950/40">
          <p className="text-xs text-green-700 dark:text-emerald-300 opacity-80">Vendas</p>
          <p className="font-bold text-green-700 dark:text-emerald-300 mt-1">
            {BRL(sessao.total_vendas || sessao.valor_fechamento_calculado)}
          </p>
        </div>
        <div className="bg-red-50 rounded-xl p-3 dark:bg-red-950/40">
          <p className="text-xs text-red-700 dark:text-red-300 opacity-80">Sangrias</p>
          <p className="font-bold text-red-700 dark:text-red-300 mt-1">{BRL(totalSangrias)}</p>
        </div>
        <div className="bg-green-50 rounded-xl p-3 dark:bg-emerald-950/40">
          <p className="text-xs text-green-700 dark:text-emerald-300 opacity-80">Suprimentos</p>
          <p className="font-bold text-green-700 dark:text-emerald-300 mt-1">{BRL(totalSuprimentos)}</p>
        </div>
      </div>

      {/* Vendas por forma de pagamento */}
      {pagamentos.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-2">
            Vendas por Forma de Pagamento
          </p>
          <div className="border border-gray-200 rounded-lg divide-y divide-gray-100 dark:border-navy-600 dark:divide-navy-700">
            {pagamentos.map((pg, i) => (
              <div key={i} className="flex justify-between px-4 py-2 text-sm">
                <span className="text-gray-600 dark:text-slate-400">{pg.forma || pg.metodo || pg.nome || '—'}</span>
                <span className="font-mono font-semibold text-gray-900 dark:text-slate-100">{BRL(pg.total || pg.valor)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Resumo de conferência */}
      <div className="border-t border-gray-200 dark:border-navy-700 pt-3 space-y-1">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600 dark:text-slate-400">Valor calculado em caixa</span>
          <span className="font-mono font-semibold text-gray-900 dark:text-slate-100">
            {BRL(sessao.valor_fechamento_calculado)}
          </span>
        </div>
        {sessao.valor_fechamento_informado != null && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-600 dark:text-slate-400">Contagem física</span>
            <span className="font-mono font-semibold text-gray-900 dark:text-slate-100">
              {BRL(sessao.valor_fechamento_informado)}
            </span>
          </div>
        )}
        <div className="flex justify-between text-sm font-semibold border-t border-gray-100 dark:border-navy-700 pt-1">
          <span className="text-gray-700 dark:text-slate-300">Diferença</span>
          <DiferencaCell valor={sessao.diferenca} />
        </div>
      </div>

      {sessao.observacoes && (
        <div className="bg-gray-50 rounded-lg p-3 dark:bg-navy-900/50">
          <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">Observações</p>
          <p className="text-sm text-gray-700 dark:text-slate-300">{sessao.observacoes}</p>
        </div>
      )}
    </div>
  )
}

export default function RelatorioSessoesCaixa() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)

  // Proteção: only staff
  useEffect(() => {
    if (user && !user.is_staff) {
      navigate('/pdv/venda', { replace: true })
    }
  }, [user, navigate])

  const [sessoes, setSessoes] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalDiferencaPagina, setTotalDiferencaPagina] = useState(0)

  // Filtros
  const [dataInicio, setDataInicio] = useState('')
  const [dataFim, setDataFim] = useState('')
  const [statusFiltro, setStatusFiltro] = useState('')
  const [contaFiltro, setContaFiltro] = useState('')
  const [contas, setContas] = useState([])
  const [operadorFiltro, setOperadorFiltro] = useState('')
  const [operadores, setOperadores] = useState([])

  // Modal detalhe
  const [sessaoDetalhe, setSessaoDetalhe] = useState(null)
  const [modalDetalhe, setModalDetalhe] = useState(false)

  // Toast
  const [toast, setToast] = useState(null)

  const mostrarToast = (msg, tipo = 'success') => {
    setToast({ msg, tipo })
    setTimeout(() => setToast(null), 4000)
  }

  const filtrosAtivos = dataInicio || dataFim || statusFiltro || contaFiltro || operadorFiltro

  // Carregar contas para o filtro
  useEffect(() => {
    api.get('/financeiro/contas/?page_size=100')
      .then(({ data }) => {
        const lista = (data.results || data || []).map((c) => ({
          value: c.id,
          label: c.nome,
        }))
        setContas(lista)
      })
      .catch(() => {})
  }, [])

  // RF-05 — sem endpoint dedicado de operadores: deriva lista distinta a
  // partir do próprio GET /pdv/sessoes/ (mesmo endpoint que a tela consome)
  useEffect(() => {
    api.get('/pdv/sessoes/', { params: { page_size: 100, ordering: '-data_abertura' } })
      .then(({ data }) => {
        const lista = data.results || []
        const mapa = new Map()
        lista.forEach((s) => {
          if (s.operador != null && !mapa.has(s.operador)) {
            mapa.set(s.operador, s.operador_nome || `Operador #${s.operador}`)
          }
        })
        const options = Array.from(mapa, ([value, label]) => ({ value, label }))
          .sort((a, b) => a.label.localeCompare(b.label))
        setOperadores(options)
      })
      .catch(() => {})
  }, [])

  const carregarSessoes = useCallback(async () => {
    if (user && !user.is_staff) return
    setLoading(true)
    try {
      const params = { page, page_size: PAGE_SIZE, ordering: '-data_abertura' }
      if (dataInicio) params.data_abertura__date__gte = dataInicio
      if (dataFim) params.data_abertura__date__lte = dataFim
      if (statusFiltro) params.status = statusFiltro
      if (contaFiltro) params.conta = contaFiltro
      if (operadorFiltro) params.operador = operadorFiltro
      const { data } = await api.get('/pdv/sessoes/', { params })
      const lista = data.results || []
      setSessoes(lista)
      const count = data.count || 0
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
      // Totalizador de diferença da página
      const totalDif = lista.reduce((s, s2) => s + Number(s2.diferenca || 0), 0)
      setTotalDiferencaPagina(totalDif)
    } catch (err) {
      mostrarToast(extractErrorMessage(err, 'Erro ao carregar sessões.'), 'error')
    } finally {
      setLoading(false)
    }
  }, [page, dataInicio, dataFim, statusFiltro, contaFiltro, operadorFiltro, user])

  useEffect(() => {
    carregarSessoes()
  }, [carregarSessoes])

  const limparFiltros = () => {
    setDataInicio('')
    setDataFim('')
    setStatusFiltro('')
    setContaFiltro('')
    setOperadorFiltro('')
    setPage(1)
  }

  const abrirDetalhe = (sessao) => {
    setSessaoDetalhe(sessao)
    setModalDetalhe(true)
  }

  const fecharDetalhe = () => {
    setModalDetalhe(false)
    setSessaoDetalhe(null)
  }

  // Enquanto user ainda não carregou, não renderiza nada
  if (!user) return null

  return (
    <div className="space-y-4">
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white ${
            toast.tipo === 'error' ? 'bg-red-600' : 'bg-accent-600'
          }`}
        >
          {toast.msg}
        </div>
      )}

      <div className="flex items-center gap-3">
        <ClipboardList size={24} className="text-gray-600 dark:text-slate-400" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Relatório de Sessões de Caixa</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-0.5">Auditoria de abertura e fechamento de caixa</p>
        </div>
      </div>

      {/* Filtros */}
      <Card>
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <p className="text-xs text-gray-500 dark:text-slate-400 mb-1 flex items-center gap-1">
              <Calendar size={12} />
              De
            </p>
            <Input
              type="date"
              value={dataInicio}
              onChange={(e) => { setDataInicio(e.target.value); setPage(1) }}
            />
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-slate-400 mb-1 flex items-center gap-1">
              <Calendar size={12} />
              Até
            </p>
            <Input
              type="date"
              value={dataFim}
              onChange={(e) => { setDataFim(e.target.value); setPage(1) }}
            />
          </div>
          <div className="w-48">
            <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">Status</p>
            <Select
              options={STATUS_OPTIONS}
              value={statusFiltro}
              onChange={(e) => { setStatusFiltro(e.target.value); setPage(1) }}
            />
          </div>
          {contas.length > 0 && (
            <div className="w-48">
              <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">Conta</p>
              <Select
                options={[{ value: '', label: 'Todas as contas' }, ...contas]}
                value={contaFiltro}
                onChange={(e) => { setContaFiltro(e.target.value); setPage(1) }}
              />
            </div>
          )}
          {operadores.length > 0 && (
            <div className="w-48">
              <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">Operador</p>
              <Select
                options={[{ value: '', label: 'Todos os operadores' }, ...operadores]}
                value={operadorFiltro}
                onChange={(e) => { setOperadorFiltro(e.target.value); setPage(1) }}
              />
            </div>
          )}
          {filtrosAtivos && (
            <Button variant="secondary" onClick={limparFiltros}>
              Limpar filtros
            </Button>
          )}
        </div>
      </Card>

      {loading ? (
        <div className="text-center py-12 text-gray-400 dark:text-slate-500 text-sm">Carregando...</div>
      ) : sessoes.length === 0 ? (
        <div className="text-center py-12 text-gray-400 dark:text-slate-500">
          <ClipboardList size={32} className="mx-auto mb-2 text-gray-300 dark:text-navy-500" />
          <p className="text-sm">Nenhuma sessão encontrada.</p>
        </div>
      ) : (
        <>
          {/* Mobile — cards */}
          <div className="flex flex-col gap-3 md:hidden">
            {sessoes.map((sessao) => {
              const temDiferenca = Number(sessao.diferenca || 0) !== 0
              return (
                <div
                  key={sessao.id}
                  className={`bg-white rounded-xl border shadow-sm cursor-pointer hover:shadow-md transition-shadow dark:shadow-none dark:hover:shadow-none ${
                    temDiferenca ? 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/30' : 'border-gray-200 dark:border-navy-600 dark:bg-navy-800'
                  }`}
                  onClick={() => abrirDetalhe(sessao)}
                >
                  <div className="px-4 py-3 space-y-2">
                    <div className="flex justify-between items-start gap-2">
                      <div className="min-w-0">
                        <p className="font-semibold text-gray-900 dark:text-slate-100 truncate">
                          {sessao.conta?.nome || sessao.conta_nome || '—'}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                          {sessao.operador_nome || '—'}
                        </p>
                      </div>
                      <Badge status={sessao.status} />
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-gray-400 dark:text-slate-500">Abertura: </span>
                        <span className="text-gray-700 dark:text-slate-300">{formatarDataHora(sessao.data_abertura)}</span>
                      </div>
                      <div>
                        <span className="text-gray-400 dark:text-slate-500">Fechamento: </span>
                        <span className="text-gray-700 dark:text-slate-300">{formatarDataHora(sessao.data_fechamento)}</span>
                      </div>
                      <div>
                        <span className="text-gray-400 dark:text-slate-500">Calculado: </span>
                        <span className="font-mono text-gray-900 dark:text-slate-100">{BRL(sessao.valor_fechamento_calculado)}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-gray-400 dark:text-slate-500">Diferença: </span>
                        <DiferencaCell valor={sessao.diferenca} />
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Desktop — tabela */}
          <div className="hidden md:block">
            <Card>
              <div className="overflow-x-auto -mx-6 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200 dark:bg-navy-900 dark:border-navy-600">
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Conta</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Operador</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Abertura</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Fechamento</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Vl. Abertura</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Calculado</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Contagem</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Diferença</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-navy-700">
                    {sessoes.map((sessao) => {
                      const temDiferenca = Number(sessao.diferenca || 0) !== 0
                      return (
                        <tr
                          key={sessao.id}
                          className={`cursor-pointer hover:bg-gray-50 transition-colors dark:hover:bg-navy-700/60 ${
                            temDiferenca ? 'bg-red-50 hover:bg-red-100 dark:bg-red-950/20 dark:hover:bg-red-950/30' : ''
                          }`}
                          onClick={() => abrirDetalhe(sessao)}
                        >
                          <td className="px-4 py-3 font-medium text-gray-900 dark:text-slate-100 max-w-[140px] truncate">
                            {sessao.conta?.nome || sessao.conta_nome || '—'}
                          </td>
                          <td className="px-4 py-3 text-gray-600 dark:text-slate-400">
                            {sessao.operador_nome || '—'}
                          </td>
                          <td className="px-4 py-3 text-gray-600 dark:text-slate-400 whitespace-nowrap">
                            {formatarDataHora(sessao.data_abertura)}
                          </td>
                          <td className="px-4 py-3 text-gray-600 dark:text-slate-400 whitespace-nowrap">
                            {formatarDataHora(sessao.data_fechamento)}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-gray-700 dark:text-slate-300">
                            {BRL(sessao.valor_abertura)}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-gray-700 dark:text-slate-300">
                            {sessao.valor_fechamento_calculado != null
                              ? BRL(sessao.valor_fechamento_calculado)
                              : '—'}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-gray-700 dark:text-slate-300">
                            {sessao.valor_fechamento_informado != null
                              ? BRL(sessao.valor_fechamento_informado)
                              : '—'}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <DiferencaCell valor={sessao.diferenca} />
                          </td>
                          <td className="px-4 py-3">
                            <Badge status={sessao.status} />
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                  {/* Totalizador da página */}
                  <tfoot>
                    <tr className="border-t-2 border-gray-300 bg-gray-50 dark:border-navy-600 dark:bg-navy-900">
                      <td colSpan={7} className="px-4 py-3 text-sm font-semibold text-gray-700 dark:text-slate-300">
                        Total de diferenças nesta página
                      </td>
                      <td className="px-4 py-3 text-right">
                        <DiferencaCell valor={totalDiferencaPagina} />
                      </td>
                      <td />
                    </tr>
                  </tfoot>
                </table>
              </div>
            </Card>
          </div>

          {/* Totalizador mobile */}
          <div className="md:hidden bg-gray-50 rounded-xl border border-gray-200 px-4 py-3 flex justify-between items-center dark:bg-navy-900/50 dark:border-navy-600">
            <span className="text-sm font-semibold text-gray-700 dark:text-slate-300">Total de diferenças (página)</span>
            <DiferencaCell valor={totalDiferencaPagina} />
          </div>

          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}

      {/* Modal — Detalhe da Sessão */}
      {modalDetalhe && sessaoDetalhe && (
        <Modal
          title={`Sessão #${sessaoDetalhe.id} — ${sessaoDetalhe.conta?.nome || sessaoDetalhe.conta_nome || 'Caixa'}`}
          onClose={fecharDetalhe}
          maxW="max-w-2xl"
        >
          <ResumoSessaoModal sessao={sessaoDetalhe} />
        </Modal>
      )}
    </div>
  )
}

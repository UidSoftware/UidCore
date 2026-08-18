import { useState, useEffect, useCallback } from 'react'
import { Eye, XCircle, Calendar, PackageSearch, RotateCcw } from 'lucide-react'
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

const STATUS_VENDA_BADGES = {
  ABERTA: 'bg-yellow-100 text-yellow-800 dark:bg-amber-900/30 dark:text-amber-300',
  FINALIZADA: 'bg-green-100 text-green-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  CANCELADA: 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400',
}

const STATUS_OPTIONS = [
  { value: '', label: 'Todos os status' },
  { value: 'ABERTA', label: 'Aberta' },
  { value: 'FINALIZADA', label: 'Finalizada' },
  { value: 'CANCELADA', label: 'Cancelada' },
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
        STATUS_VENDA_BADGES[status] || 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400'
      }`}
    >
      {status}
    </span>
  )
}

export default function HistoricoVendas() {
  const user = useAuthStore((s) => s.user)

  const [vendas, setVendas] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  // Filtros
  const [dataInicio, setDataInicio] = useState('')
  const [dataFim, setDataFim] = useState('')
  const [statusFiltro, setStatusFiltro] = useState('')

  // Modal detalhe
  const [vendaDetalhe, setVendaDetalhe] = useState(null)
  const [modalDetalhe, setModalDetalhe] = useState(false)

  // Modal cancelar
  const [vendaCancelar, setVendaCancelar] = useState(null)
  const [modalCancelar, setModalCancelar] = useState(false)
  const [motivoCancelamento, setMotivoCancelamento] = useState('')
  const [cancelando, setCancelando] = useState(false)

  // Modal devolucao de item
  const [itemDevolucao, setItemDevolucao] = useState(null)
  const [modalDevolucao, setModalDevolucao] = useState(false)
  const [qtdDevolucao, setQtdDevolucao] = useState('')
  const [motivoDevolucao, setMotivoDevolucao] = useState('')
  const [devolvendo, setDevolvendo] = useState(false)

  // Toast
  const [toast, setToast] = useState(null)

  const mostrarToast = (msg, tipo = 'success') => {
    setToast({ msg, tipo })
    setTimeout(() => setToast(null), 4000)
  }

  const filtrosAtivos = dataInicio || dataFim || statusFiltro

  const carregarVendas = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page, page_size: PAGE_SIZE, ordering: '-data_hora' }
      if (dataInicio) params.data_hora__date__gte = dataInicio
      if (dataFim) params.data_hora__date__lte = dataFim
      if (statusFiltro) params.status = statusFiltro
      const { data } = await api.get('/pdv/vendas/', { params })
      setVendas(data.results || [])
      const count = data.count || 0
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
    } catch (err) {
      mostrarToast(extractErrorMessage(err, 'Erro ao carregar vendas.'), 'error')
    } finally {
      setLoading(false)
    }
  }, [page, dataInicio, dataFim, statusFiltro])

  useEffect(() => {
    carregarVendas()
  }, [carregarVendas])

  const limparFiltros = () => {
    setDataInicio('')
    setDataFim('')
    setStatusFiltro('')
    setPage(1)
  }

  const abrirDetalhe = (venda) => {
    setVendaDetalhe(venda)
    setModalDetalhe(true)
  }

  const fecharDetalhe = () => {
    setModalDetalhe(false)
    setVendaDetalhe(null)
  }

  const abrirCancelar = (venda) => {
    setVendaCancelar(venda)
    setMotivoCancelamento('')
    setModalCancelar(true)
  }

  const fecharCancelar = () => {
    setModalCancelar(false)
    setVendaCancelar(null)
    setMotivoCancelamento('')
  }

  const confirmarCancelamento = async () => {
    if (!motivoCancelamento.trim()) {
      mostrarToast('Informe o motivo do cancelamento.', 'error')
      return
    }
    setCancelando(true)
    try {
      await api.post(`/pdv/vendas/${vendaCancelar.id}/cancelar/`, {
        motivo: motivoCancelamento.trim(),
      })
      mostrarToast('Venda cancelada com sucesso.')
      fecharCancelar()
      fecharDetalhe()
      carregarVendas()
    } catch (err) {
      mostrarToast(extractErrorMessage(err, 'Erro ao cancelar venda.'), 'error')
    } finally {
      setCancelando(false)
    }
  }

  const abrirDevolucao = (item, qtdMax) => {
    setItemDevolucao({ ...item, qtdMax })
    setQtdDevolucao(String(qtdMax))
    setMotivoDevolucao('')
    setModalDevolucao(true)
  }

  const fecharDevolucao = () => {
    setModalDevolucao(false)
    setItemDevolucao(null)
    setQtdDevolucao('')
    setMotivoDevolucao('')
  }

  const confirmarDevolucao = async () => {
    if (!motivoDevolucao.trim()) {
      mostrarToast('Informe o motivo da devolução.', 'error')
      return
    }
    if (!qtdDevolucao || Number(qtdDevolucao) <= 0) {
      mostrarToast('Informe a quantidade a devolver.', 'error')
      return
    }
    setDevolvendo(true)
    try {
      await api.post(`/pdv/vendas/${vendaDetalhe.id}/itens/${itemDevolucao.id}/devolver/`, {
        quantidade: qtdDevolucao,
        motivo: motivoDevolucao.trim(),
      })
      mostrarToast('Devolução registrada com sucesso.')
      fecharDevolucao()
      // Recarregar detalhe se ainda estiver aberto
      if (modalDetalhe && vendaDetalhe) {
        const { data } = await api.get(`/pdv/vendas/${vendaDetalhe.id}/`)
        setVendaDetalhe(data)
      }
      carregarVendas()
    } catch (err) {
      mostrarToast(extractErrorMessage(err, 'Erro ao registrar devolução.'), 'error')
    } finally {
      setDevolvendo(false)
    }
  }

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

      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Histórico de Vendas</h1>
        <p className="text-sm text-gray-500 mt-0.5 dark:text-slate-400">Consulte e gerencie as vendas realizadas</p>
      </div>

      {/* Filtros */}
      <Card>
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <p className="text-xs text-gray-500 mb-1 flex items-center gap-1 dark:text-slate-400">
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
            <p className="text-xs text-gray-500 mb-1 flex items-center gap-1 dark:text-slate-400">
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
            <p className="text-xs text-gray-500 mb-1 dark:text-slate-400">Status</p>
            <Select
              options={STATUS_OPTIONS}
              value={statusFiltro}
              onChange={(e) => { setStatusFiltro(e.target.value); setPage(1) }}
            />
          </div>
          {filtrosAtivos && (
            <Button variant="secondary" onClick={limparFiltros}>
              Limpar filtros
            </Button>
          )}
        </div>
      </Card>

      {loading ? (
        <div className="text-center py-12 text-gray-400 text-sm dark:text-slate-500">Carregando...</div>
      ) : vendas.length === 0 ? (
        <div className="text-center py-12 text-gray-400 dark:text-slate-500">
          <PackageSearch size={32} className="mx-auto mb-2 text-gray-300 dark:text-navy-500" />
          <p className="text-sm">Nenhuma venda encontrada.</p>
        </div>
      ) : (
        <>
          {/* Mobile — cards */}
          <div className="flex flex-col gap-3 md:hidden">
            {vendas.map((venda) => (
              <Card key={venda.id}>
                <div className="flex justify-between items-start gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-gray-900 dark:text-slate-100">
                      #{venda.numero || venda.id}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5 dark:text-slate-400">
                      {formatarDataHora(venda.data_hora)}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-slate-400">
                      {venda.cliente?.nome_completo || venda.cliente?.nome_razao_social || 'Consumidor Final'}
                    </p>
                  </div>
                  <Badge status={venda.status} />
                </div>
                <div className="mt-2 flex justify-between items-center">
                  <span
                    className={`text-lg font-bold ${
                      venda.status === 'CANCELADA' ? 'line-through text-gray-400 dark:text-slate-500' : 'text-gray-900 dark:text-slate-100'
                    }`}
                  >
                    {BRL(venda.valor_total)}
                  </span>
                  <span className="text-xs text-gray-400 dark:text-slate-500">
                    {venda.operador_nome || '—'}
                  </span>
                </div>
                <div className="mt-3 flex gap-2 flex-wrap">
                  <Button size="sm" variant="secondary" onClick={() => abrirDetalhe(venda)}>
                    <Eye size={14} className="mr-1" />
                    Ver
                  </Button>
                  {venda.status === 'FINALIZADA' && user?.is_staff && (
                    <Button size="sm" variant="danger" onClick={() => abrirCancelar(venda)}>
                      <XCircle size={14} className="mr-1" />
                      Cancelar
                    </Button>
                  )}
                </div>
              </Card>
            ))}
          </div>

          {/* Desktop — tabela */}
          <div className="hidden md:block">
            <Card>
              <div className="overflow-x-auto -mx-6 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200 dark:bg-navy-900 dark:border-navy-600">
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Número</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Data/Hora</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Operador</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Cliente</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Total</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Status</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-navy-700">
                    {vendas.map((venda) => (
                      <tr key={venda.id} className="hover:bg-gray-50 dark:hover:bg-navy-700/60">
                        <td className="px-4 py-3 font-medium text-gray-900 dark:text-slate-100">
                          #{venda.numero || venda.id}
                        </td>
                        <td className="px-4 py-3 text-gray-600 dark:text-slate-400">
                          {formatarDataHora(venda.data_hora)}
                        </td>
                        <td className="px-4 py-3 text-gray-600 dark:text-slate-400">
                          {venda.operador_nome || '—'}
                        </td>
                        <td className="px-4 py-3 text-gray-600 max-w-[150px] truncate dark:text-slate-400">
                          {venda.cliente?.nome_completo || venda.cliente?.nome_razao_social || 'Consumidor Final'}
                        </td>
                        <td
                          className={`px-4 py-3 text-right font-mono font-semibold ${
                            venda.status === 'CANCELADA'
                              ? 'line-through text-gray-400 dark:text-slate-500'
                              : 'text-gray-900 dark:text-slate-100'
                          }`}
                        >
                          {BRL(venda.valor_total)}
                        </td>
                        <td className="px-4 py-3">
                          <Badge status={venda.status} />
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => abrirDetalhe(venda)}
                              className="text-gray-400 hover:text-gray-700 transition-colors dark:text-slate-500 dark:hover:text-slate-200"
                              title="Ver detalhe"
                            >
                              <Eye size={16} />
                            </button>
                            {venda.status === 'FINALIZADA' && user?.is_staff && (
                              <button
                                type="button"
                                onClick={() => abrirCancelar(venda)}
                                className="text-red-400 hover:text-red-600 transition-colors dark:text-red-400/70 dark:hover:text-red-400"
                                title="Cancelar venda"
                              >
                                <XCircle size={16} />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}

      {/* Modal — Detalhe da Venda */}
      {modalDetalhe && vendaDetalhe && (
        <Modal
          title={`Venda #${vendaDetalhe.numero || vendaDetalhe.id}`}
          onClose={fecharDetalhe}
          maxW="max-w-2xl"
        >
          <div className="space-y-4">
            {/* Cabeçalho */}
            <div className="flex flex-wrap gap-2 items-center text-sm text-gray-600 dark:text-slate-400">
              <Badge status={vendaDetalhe.status} />
              <span>
                {vendaDetalhe.cliente?.nome_completo ||
                  vendaDetalhe.cliente?.nome_razao_social ||
                  'Consumidor Final'}
              </span>
              <span className="text-gray-300 dark:text-slate-600">·</span>
              <span>
                {vendaDetalhe.operador_nome || '—'}
              </span>
              <span className="text-gray-300 dark:text-slate-600">·</span>
              <span>{formatarDataHora(vendaDetalhe.data_hora)}</span>
            </div>

            {/* Itens */}
            {vendaDetalhe.itens && vendaDetalhe.itens.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                  Itens
                </p>
                <div className="border border-gray-200 rounded-lg divide-y divide-gray-100 dark:border-navy-600 dark:divide-navy-700">
                  {vendaDetalhe.itens.map((item) => {
                    const qtdRestante =
                      Number(item.quantidade || 0) - Number(item.quantidade_estornada || 0)
                    const totalDevolvido = Number(item.quantidade_estornada || 0) > 0
                    const parcialmenteDevolvido =
                      totalDevolvido && qtdRestante > 0

                    return (
                      <div key={item.id} className="px-4 py-3">
                        <div className="flex justify-between items-start gap-2">
                          <div className="min-w-0 flex-1">
                            <p className="font-medium text-gray-900 dark:text-slate-100 truncate">
                              {item.produto?.nome || `Produto #${item.produto}`}
                            </p>
                            {parcialmenteDevolvido && (
                              <span className="inline-block mt-0.5 px-1.5 py-0.5 rounded text-xs bg-yellow-50 text-yellow-700 dark:bg-amber-900/30 dark:text-amber-300">
                                Parcialmente devolvido ({item.quantidade_estornada} un)
                              </span>
                            )}
                            <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                              {item.quantidade} ×{' '}
                              {BRL(item.valor_unitario)}
                              {Number(item.desconto_item || 0) > 0 && (
                                <span className="text-gray-400 dark:text-slate-500">
                                  {' '}
                                  — {BRL(item.desconto_item)} desconto
                                </span>
                              )}
                            </p>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <span className="font-mono font-semibold text-gray-900 dark:text-slate-100">
                              {BRL(item.valor_total)}
                            </span>
                            {vendaDetalhe.status === 'FINALIZADA' && qtdRestante > 0 && (
                              <button
                                type="button"
                                onClick={() => abrirDevolucao(item, qtdRestante)}
                                className="text-yellow-600 hover:text-yellow-800 transition-colors dark:text-amber-400 dark:hover:text-amber-300"
                                title="Devolver item"
                              >
                                <RotateCcw size={14} />
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Pagamentos */}
            {vendaDetalhe.pagamentos && vendaDetalhe.pagamentos.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                  Pagamentos
                </p>
                <div className="space-y-1">
                  {vendaDetalhe.pagamentos.map((pg, i) => (
                    <div key={i} className="flex justify-between text-sm">
                      <span className="text-gray-600 dark:text-slate-400">
                        {pg.metodo?.nome || pg.forma_pagamento || 'Pagamento'}
                      </span>
                      <span className="font-mono text-gray-900 dark:text-slate-100">{BRL(pg.valor)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Total */}
            <div className="border-t border-gray-200 dark:border-navy-700 pt-3 flex justify-between items-center">
              <span className="font-semibold text-gray-700 dark:text-slate-300">Total</span>
              <span
                className={`font-mono font-bold text-lg ${
                  vendaDetalhe.status === 'CANCELADA' ? 'line-through text-gray-400 dark:text-slate-500' : 'text-gray-900 dark:text-slate-100'
                }`}
              >
                {BRL(vendaDetalhe.valor_total)}
              </span>
            </div>

            {/* Ações */}
            {vendaDetalhe.status === 'FINALIZADA' && user?.is_staff && (
              <div className="flex justify-end pt-2">
                <Button
                  variant="danger"
                  onClick={() => {
                    fecharDetalhe()
                    abrirCancelar(vendaDetalhe)
                  }}
                >
                  <XCircle size={16} className="mr-1" />
                  Cancelar Venda
                </Button>
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Modal — Cancelar Venda */}
      {modalCancelar && vendaCancelar && (
        <Modal
          title={`Cancelar Venda #${vendaCancelar.numero || vendaCancelar.id}`}
          onClose={fecharCancelar}
          maxW="max-w-md"
        >
          <div className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-slate-400">
              Esta ação cancelará a venda inteira. Todo o estoque será revertido e os pagamentos
              estornados.
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                Motivo <span className="text-red-500 dark:text-red-400">*</span>
              </label>
              <textarea
                rows={3}
                value={motivoCancelamento}
                onChange={(e) => setMotivoCancelamento(e.target.value)}
                placeholder="Descreva o motivo do cancelamento..."
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" onClick={fecharCancelar}>
                Voltar
              </Button>
              <Button variant="danger" loading={cancelando} onClick={confirmarCancelamento}>
                Confirmar Cancelamento
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal — Devolução de Item */}
      {modalDevolucao && itemDevolucao && (
        <Modal
          title="Devolver Item"
          onClose={fecharDevolucao}
          maxW="max-w-md"
        >
          <div className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-slate-400">
              <strong className="text-gray-900 dark:text-slate-100">{itemDevolucao.produto?.nome || `Produto #${itemDevolucao.produto}`}</strong>
              {' '}— máximo {itemDevolucao.qtdMax} unidade(s) disponíveis para devolução.
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                Quantidade a devolver <span className="text-red-500 dark:text-red-400">*</span>
              </label>
              <Input
                type="number"
                min="1"
                max={itemDevolucao.qtdMax}
                step="1"
                value={qtdDevolucao}
                onChange={(e) => setQtdDevolucao(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                Motivo <span className="text-red-500 dark:text-red-400">*</span>
              </label>
              <textarea
                rows={2}
                value={motivoDevolucao}
                onChange={(e) => setMotivoDevolucao(e.target.value)}
                placeholder="Motivo da devolução..."
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" onClick={fecharDevolucao}>
                Cancelar
              </Button>
              <Button loading={devolvendo} onClick={confirmarDevolucao}>
                Confirmar Devolução
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}

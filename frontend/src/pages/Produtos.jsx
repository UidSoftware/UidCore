import { useState, useEffect, useCallback, useRef } from 'react'
import { Plus, Trash2, ArrowRight } from 'lucide-react'
import api from '../api/client.js'
import { extractErrorMessage, stripEmptyStrings } from '../utils/errors.js'
import Card from '../components/ui/Card.jsx'
import Button from '../components/ui/Button.jsx'
import Input from '../components/ui/Input.jsx'
import Select from '../components/ui/Select.jsx'
import Modal from '../components/ui/Modal.jsx'
import Pagination from '../components/ui/Pagination.jsx'

const PAGE_SIZE = 10

const UNIDADE_OPTIONS = [
  { value: 'UN', label: 'UN — Unidade' },
  { value: 'PT', label: 'PT — Pacote' },
  { value: 'CX', label: 'CX — Caixa' },
  { value: 'KG', label: 'KG — Quilograma' },
  { value: 'L', label: 'L — Litro' },
  { value: 'M', label: 'M — Metro' },
]

const UNIDADE_SELECT = [
  { value: '', label: 'Selecione...' },
  ...UNIDADE_OPTIONS,
]

const BRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

const EMPTY_CONVERSAO = { unidade: '', converte_para: '', quantidade_por_base: '' }

const unidadeLabel = (valor) => UNIDADE_OPTIONS.find((u) => u.value === valor)?.label || valor

const formatFator = (n) =>
  Number(n).toLocaleString('pt-BR', { maximumFractionDigits: 3 })

// RF-04/RF-08: resolve o fator de conversao de `unidade` ate `unidadeBase`
// percorrendo a cadeia de `converte_para` (mesma logica recursiva do backend
// produtos/services.py::fator_para_base) — so para preview no cliente, a
// fonte de verdade continua sendo a validacao do servidor no submit.
function resolverFatorBase(conversoes, unidadeBase, unidade, _visitados = new Set(), _profundidade = 0) {
  if (unidade === unidadeBase) return { ok: true, fator: 1 }
  if (_visitados.has(unidade)) return { ok: false }
  if (_profundidade >= 5) return { ok: false }

  const conv = conversoes.find((c) => c.unidade === unidade)
  if (!conv || !conv.quantidade_por_base) return { ok: false }

  const proximaUnidade = conv.converte_para || unidadeBase
  const novosVisitados = new Set(_visitados)
  novosVisitados.add(unidade)
  const resto = resolverFatorBase(conversoes, unidadeBase, proximaUnidade, novosVisitados, _profundidade + 1)
  if (!resto.ok) return { ok: false }
  return { ok: true, fator: parseFloat(conv.quantidade_por_base) * resto.fator }
}

const EMPTY_FORM = {
  nome: '',
  codigo_barras: '',
  unidade_base: 'UN',
  quantidade_estoque: '',
  estoque_minimo: '',
  valor_unitario: '',
  preco_venda: '',
  observacoes: '',
}

export default function Produtos() {
  const [produtos, setProdutos] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)
  const [conversoes, setConversoes] = useState([])
  const [entradas, setEntradas] = useState([])
  const [loadingEntradas, setLoadingEntradas] = useState(false)
  const [novaEntrada, setNovaEntrada] = useState(null)
  const [savingEntrada, setSavingEntrada] = useState(false)
  // Snapshot das conversoes carregadas do backend (id -> {unidade, converte_para,
  // quantidade_por_base}) — usado no handleSubmit pra so fazer PATCH das linhas
  // que realmente mudaram (RF-02).
  const conversoesSnapshotRef = useRef({})

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), type === 'error' ? 7000 : 3500)
  }

  const fetchProdutos = useCallback(async () => {
    setLoading(true)
    try {
      const response = await api.get('/produtos/', {
        params: { search, page, page_size: PAGE_SIZE },
      })
      setProdutos(response.data.results)
      const count = response.data.count
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
    } catch {
      showToast('Erro ao carregar produtos.', 'error')
    } finally {
      setLoading(false)
    }
  }, [search, page])

  useEffect(() => {
    fetchProdutos()
  }, [fetchProdutos])

  const openNew = () => {
    setForm(EMPTY_FORM)
    setConversoes([])
    setEntradas([])
    setNovaEntrada(null)
    setEditingId(null)
    conversoesSnapshotRef.current = {}
    setModalOpen(true)
  }

  const openEdit = async (produto) => {
    setForm({
      nome: produto.nome || '',
      codigo_barras: produto.codigo_barras || '',
      unidade_base: produto.unidade_base || 'UN',
      quantidade_estoque: produto.quantidade_estoque || '',
      estoque_minimo: produto.estoque_minimo || '',
      valor_unitario: produto.valor_unitario || '',
      preco_venda: produto.preco_venda || '',
      observacoes: produto.observacoes || '',
    })
    setEditingId(produto.id)
    setConversoes([])
    setEntradas([])
    setNovaEntrada(null)
    conversoesSnapshotRef.current = {}
    setModalOpen(true)

    // Carregar conversoes e entradas em paralelo
    setLoadingEntradas(true)
    try {
      const [convR, entR] = await Promise.all([
        api.get(`/produtos/${produto.id}/conversoes/`).catch(() => ({ data: [] })),
        api.get(`/produtos/${produto.id}/entradas/`).catch(() => ({ data: [] })),
      ])
      const convList = convR.data.results || convR.data || []
      setConversoes(convList)
      const snapshot = {}
      convList.forEach((c) => {
        snapshot[c.id] = {
          unidade: c.unidade,
          converte_para: c.converte_para || '',
          quantidade_por_base: c.quantidade_por_base,
        }
      })
      conversoesSnapshotRef.current = snapshot
      setEntradas(entR.data.results || entR.data || [])
    } finally {
      setLoadingEntradas(false)
    }
  }

  const closeModal = () => {
    setModalOpen(false)
    setEditingId(null)
    setForm(EMPTY_FORM)
    setConversoes([])
    setEntradas([])
    setNovaEntrada(null)
    conversoesSnapshotRef.current = {}
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  // Conversoes
  const addConversao = () => {
    setConversoes((prev) => [...prev, { ...EMPTY_CONVERSAO }])
  }

  const removeConversao = async (idx) => {
    const conv = conversoes[idx]
    // RF-03: linha ja persistida (tem id) precisa de DELETE real no backend —
    // so sumir do estado local deixava a conversao viva no banco. RN-06:
    // backend bloqueia excluir uma conversao usada como elo por outra —
    // exibir a mensagem completa (lista de dependentes) sem truncar.
    if (conv.id && editingId) {
      try {
        await api.delete(`/produtos/${editingId}/conversoes/${conv.id}/`)
      } catch (error) {
        showToast(extractErrorMessage(error, 'Erro ao remover conversao.'), 'error')
        return
      }
      delete conversoesSnapshotRef.current[conv.id]
    }
    setConversoes((prev) => prev.filter((_, i) => i !== idx))
  }

  const updateConversao = (idx, field, value) => {
    setConversoes((prev) =>
      prev.map((c, i) => (i === idx ? { ...c, [field]: value } : c))
    )
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = stripEmptyStrings(form)
      let produtoId = editingId
      if (editingId) {
        await api.patch(`/produtos/${editingId}/`, payload)
        showToast('Produto atualizado com sucesso.')
      } else {
        const r = await api.post('/produtos/', payload)
        produtoId = r.data.id
        showToast('Produto cadastrado com sucesso.')
      }
      // Salvar conversoes — POST das novas, PATCH das existentes que mudaram (RF-02)
      if (produtoId) {
        for (const conv of conversoes) {
          if (!conv.unidade || !conv.quantidade_por_base) continue
          const payload = stripEmptyStrings({
            unidade: conv.unidade,
            converte_para: conv.converte_para,
            quantidade_por_base: conv.quantidade_por_base,
          })
          if (conv.id) {
            const original = conversoesSnapshotRef.current[conv.id]
            const mudou =
              !original ||
              original.unidade !== conv.unidade ||
              (original.converte_para || '') !== (conv.converte_para || '') ||
              Number(original.quantidade_por_base) !== Number(conv.quantidade_por_base)
            if (!mudou) continue
            try {
              await api.patch(`/produtos/${produtoId}/conversoes/${conv.id}/`, payload)
              conversoesSnapshotRef.current[conv.id] = {
                unidade: conv.unidade,
                converte_para: conv.converte_para || '',
                quantidade_por_base: conv.quantidade_por_base,
              }
            } catch (error) {
              showToast(extractErrorMessage(error, 'Erro ao atualizar conversao.'), 'error')
            }
          } else {
            try {
              await api.post(`/produtos/${produtoId}/conversoes/`, payload)
            } catch (error) {
              showToast(extractErrorMessage(error, 'Erro ao adicionar conversao.'), 'error')
            }
          }
        }
      }
      closeModal()
      fetchProdutos()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao salvar produto.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (produto) => {
    if (!window.confirm(`Excluir o produto "${produto.nome}"?`)) return
    try {
      await api.delete(`/produtos/${produto.id}/`)
      showToast('Produto removido.')
      fetchProdutos()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao remover produto.'), 'error')
    }
  }

  const handleSearchChange = (e) => {
    setSearch(e.target.value)
    setPage(1)
  }

  const handleRegistrarEntrada = async (e) => {
    e.preventDefault()
    if (!novaEntrada || !editingId) return
    setSavingEntrada(true)
    try {
      await api.post(`/produtos/${editingId}/entradas/`, stripEmptyStrings(novaEntrada))
      showToast('Entrada registrada.')
      setNovaEntrada(null)
      // Recarregar entradas e produto
      const [entR, prodR] = await Promise.all([
        api.get(`/produtos/${editingId}/entradas/`).catch(() => ({ data: [] })),
        api.get(`/produtos/${editingId}/`).catch(() => ({ data: null })),
      ])
      setEntradas(entR.data.results || entR.data || [])
      if (prodR.data) {
        setForm((prev) => ({
          ...prev,
          quantidade_estoque: prodR.data.quantidade_estoque || prev.quantidade_estoque,
        }))
      }
      fetchProdutos()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao registrar entrada.'), 'error')
    } finally {
      setSavingEntrada(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white whitespace-pre-line break-words ${
            toast.type === 'error' ? 'bg-red-600' : 'bg-accent-600'
          }`}
        >
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Produtos</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-0.5">Gestao de estoque e catalogo de produtos</p>
        </div>
        <Button onClick={openNew}>+ Novo Produto</Button>
      </div>

      {/* Search */}
      <Card>
        <Input
          placeholder="Buscar por nome, codigo de barras..."
          value={search}
          onChange={handleSearchChange}
        />
      </Card>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-12 text-gray-400 dark:text-slate-500 text-sm">Carregando...</div>
      ) : produtos.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400 dark:text-slate-500">
          <span className="text-4xl">📦</span>
          <p className="text-sm">Nenhum produto encontrado.</p>
        </div>
      ) : (
        <>
          {/* Mobile cards */}
          <div className="flex flex-col gap-3 md:hidden">
            {produtos.map((p) => (
              <Card key={p.id}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-gray-900 truncate dark:text-slate-100">{p.nome}</p>
                    {p.codigo_barras && (
                      <p className="text-xs text-gray-500 mt-0.5 dark:text-slate-400">{p.codigo_barras}</p>
                    )}
                  </div>
                  <span className={`shrink-0 text-xs rounded-full px-2 py-0.5 font-medium ${
                    p.is_active ? 'bg-green-100 text-green-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-gray-100 text-gray-500 dark:bg-navy-700 dark:text-slate-400'
                  }`}>
                    {p.is_active ? 'Ativo' : 'Inativo'}
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs text-gray-600 dark:text-slate-400">
                  <div>
                    <span className="text-gray-400 dark:text-slate-500">Estoque</span>
                    <p className="font-medium text-gray-800 dark:text-slate-200">{p.quantidade_estoque || 0} {p.unidade_base}</p>
                  </div>
                  <div>
                    <span className="text-gray-400 dark:text-slate-500">Preco Venda</span>
                    <p className="font-medium text-gray-800 dark:text-slate-200">{BRL(p.preco_venda)}</p>
                  </div>
                </div>
                <div className="mt-3 flex gap-2">
                  <Button size="sm" variant="secondary" onClick={() => openEdit(p)}>Editar</Button>
                  <Button size="sm" variant="danger" onClick={() => handleDelete(p)}>Excluir</Button>
                </div>
              </Card>
            ))}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block">
            <Card>
              <div className="overflow-x-auto -mx-6 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200 dark:bg-navy-900 dark:border-navy-600">
                      <th className="text-left px-6 py-3 font-semibold text-gray-600 whitespace-nowrap dark:text-slate-400">Nome</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap dark:text-slate-400">Cod. Barras</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap dark:text-slate-400">Estoque</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600 whitespace-nowrap dark:text-slate-400">Preco Venda</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap dark:text-slate-400">Status</th>
                      <th className="text-right px-6 py-3 font-semibold text-gray-600 whitespace-nowrap dark:text-slate-400">Acoes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-navy-700">
                    {produtos.map((p) => (
                      <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-navy-700/60 transition-colors">
                        <td className="px-6 py-3 font-medium text-gray-900 whitespace-nowrap max-w-[200px] truncate dark:text-slate-100">
                          {p.nome}
                        </td>
                        <td className="px-4 py-3 text-gray-600 whitespace-nowrap dark:text-slate-400">{p.codigo_barras || '—'}</td>
                        <td className="px-4 py-3 text-gray-600 whitespace-nowrap dark:text-slate-400">
                          {p.quantidade_estoque || 0} {p.unidade_base}
                        </td>
                        <td className="px-4 py-3 text-right font-semibold text-gray-900 whitespace-nowrap dark:text-slate-100">
                          {BRL(p.preco_venda)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${
                            p.is_active ? 'bg-green-100 text-green-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-gray-100 text-gray-500 dark:bg-navy-700 dark:text-slate-400'
                          }`}>
                            {p.is_active ? 'Ativo' : 'Inativo'}
                          </span>
                        </td>
                        <td className="px-6 py-3 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-2">
                            <Button size="sm" variant="secondary" onClick={() => openEdit(p)}>Editar</Button>
                            <Button size="sm" variant="danger" onClick={() => handleDelete(p)}>Excluir</Button>
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

      {/* Modal */}
      {modalOpen && (
        <Modal
          title={editingId ? 'Editar Produto' : 'Novo Produto'}
          onClose={closeModal}
          maxW="max-w-2xl"
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Nome"
                name="nome"
                value={form.nome}
                onChange={handleChange}
                placeholder="Nome do produto"
                required
              />
              <Input
                label="Codigo de Barras"
                name="codigo_barras"
                value={form.codigo_barras}
                onChange={handleChange}
                placeholder="EAN, ISBN..."
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Select
                label="Unidade Base"
                name="unidade_base"
                options={UNIDADE_OPTIONS}
                value={form.unidade_base}
                onChange={handleChange}
              />
              <Input
                label="Qtd em Estoque"
                name="quantidade_estoque"
                type="number"
                step="0.001"
                min="0"
                value={form.quantidade_estoque}
                onChange={handleChange}
                placeholder="0"
              />
              <Input
                label="Estoque Minimo"
                name="estoque_minimo"
                type="number"
                step="0.001"
                min="0"
                value={form.estoque_minimo}
                onChange={handleChange}
                placeholder="0"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Valor Unitario / Custo (R$)"
                name="valor_unitario"
                type="number"
                step="0.01"
                min="0"
                value={form.valor_unitario}
                onChange={handleChange}
                placeholder="0,00"
              />
              <Input
                label="Preco de Venda (R$)"
                name="preco_venda"
                type="number"
                step="0.01"
                min="0"
                value={form.preco_venda}
                onChange={handleChange}
                placeholder="0,00"
              />
            </div>

            {/* Secao Conversoes */}
            <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 dark:bg-navy-900/50 dark:border-navy-700">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">Conversoes de Unidade</h3>
                <button
                  type="button"
                  onClick={addConversao}
                  className="flex items-center gap-1 text-xs text-primary-600 font-medium hover:text-primary-800 transition-colors dark:text-violet-400 dark:hover:text-violet-300"
                >
                  <Plus size={14} />
                  Adicionar Conversao
                </button>
              </div>
              {conversoes.length === 0 && (
                <p className="text-xs text-gray-400 dark:text-slate-500">Nenhuma conversao cadastrada. Ex.: CX = 30 UN</p>
              )}
              <div className="space-y-2">
                {conversoes.map((conv, idx) => {
                  const unidadeBase = form.unidade_base || 'UN'
                  const convertePara = conv.converte_para || unidadeBase
                  // Converte-para: unidade base do produto (sempre primeira opcao)
                  // + demais unidades ja usadas em outras linhas, exceto a propria.
                  const converteParaOptions = [
                    { value: unidadeBase, label: `${unidadeLabel(unidadeBase)} (base)` },
                    ...conversoes
                      .filter((c, i) => i !== idx && c.unidade && c.unidade !== unidadeBase)
                      .map((c) => ({ value: c.unidade, label: unidadeLabel(c.unidade) }))
                      .filter((opt, i, arr) => arr.findIndex((o) => o.value === opt.value) === i),
                  ]
                  const resultado =
                    conv.unidade && conv.quantidade_por_base
                      ? resolverFatorBase(conversoes, unidadeBase, conv.unidade)
                      : null
                  return (
                    <div key={idx} className="space-y-1">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                        <div className="flex-1">
                          <Select
                            label="Unidade"
                            options={UNIDADE_SELECT}
                            value={conv.unidade}
                            onChange={(e) => updateConversao(idx, 'unidade', e.target.value)}
                          />
                        </div>
                        <div className="flex-1">
                          <Select
                            label="Converte para"
                            options={converteParaOptions}
                            value={convertePara}
                            onChange={(e) =>
                              updateConversao(
                                idx,
                                'converte_para',
                                e.target.value === unidadeBase ? '' : e.target.value,
                              )
                            }
                          />
                        </div>
                        <div className="flex-1 flex items-end gap-2">
                          <div className="flex-1">
                            <Input
                              label={`Qtd por ${unidadeLabel(convertePara)}`}
                              type="number"
                              step="0.001"
                              min="0"
                              value={conv.quantidade_por_base}
                              onChange={(e) => updateConversao(idx, 'quantidade_por_base', e.target.value)}
                              placeholder="30"
                            />
                          </div>
                          <button
                            type="button"
                            onClick={() => removeConversao(idx)}
                            className="mb-1 text-red-400 hover:text-red-600 transition-colors p-1 dark:text-red-400/70 dark:hover:text-red-400"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                      {conv.unidade && conv.quantidade_por_base && (
                        resultado?.ok ? (
                          <p className="text-xs text-gray-500 dark:text-slate-400 pl-1 flex items-center gap-1">
                            <ArrowRight size={12} className="text-gray-400 dark:text-slate-500 shrink-0" />
                            <span>
                              1 {conv.unidade} = {conv.quantidade_por_base} {convertePara}
                              {convertePara !== unidadeBase && (
                                <> = {formatFator(resultado.fator)} {unidadeBase}</>
                              )}
                            </span>
                          </p>
                        ) : (
                          <p className="text-xs text-amber-700 dark:text-amber-400 pl-1">
                            ⚠ conversao nao fecha na unidade base
                          </p>
                        )
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Entradas de estoque (somente edicao) */}
            {editingId && (
              <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 dark:bg-navy-900/50 dark:border-navy-700">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">Entradas de Estoque</h3>
                  {!novaEntrada && (
                    <button
                      type="button"
                      onClick={() =>
                        setNovaEntrada({ quantidade: '', unidade: form.unidade_base, nota_fiscal: '', observacoes: '' })
                      }
                      className="flex items-center gap-1 text-xs text-primary-600 font-medium hover:text-primary-800 transition-colors dark:text-violet-400 dark:hover:text-violet-300"
                    >
                      <Plus size={14} />
                      Registrar Entrada
                    </button>
                  )}
                </div>

                {/* Formulario nova entrada */}
                {novaEntrada && (
                  <div className="bg-white rounded-lg border border-gray-200 p-3 mb-3 space-y-2 dark:bg-navy-800 dark:border-navy-600">
                    <div className="grid grid-cols-2 gap-2">
                      <Input
                        label="Quantidade"
                        type="number"
                        step="0.001"
                        min="0"
                        value={novaEntrada.quantidade}
                        onChange={(e) => setNovaEntrada((p) => ({ ...p, quantidade: e.target.value }))}
                        placeholder="0"
                      />
                      <Select
                        label="Unidade"
                        options={UNIDADE_OPTIONS}
                        value={novaEntrada.unidade}
                        onChange={(e) => setNovaEntrada((p) => ({ ...p, unidade: e.target.value }))}
                      />
                    </div>
                    {/* RF-08: preview da quantidade equivalente em unidade base */}
                    {novaEntrada.unidade &&
                      novaEntrada.unidade !== form.unidade_base &&
                      novaEntrada.quantidade && (() => {
                        const resultado = resolverFatorBase(conversoes, form.unidade_base || 'UN', novaEntrada.unidade)
                        if (!resultado.ok) {
                          return (
                            <p className="text-xs text-amber-700 dark:text-amber-400">
                              ⚠ sem conversao cadastrada para esta unidade
                            </p>
                          )
                        }
                        const convertido = parseFloat(novaEntrada.quantidade) * resultado.fator
                        return (
                          <p className="text-xs text-gray-500 dark:text-slate-400">
                            = {formatFator(convertido)} {form.unidade_base}
                          </p>
                        )
                      })()}
                    <Input
                      label="Nota Fiscal"
                      value={novaEntrada.nota_fiscal}
                      onChange={(e) => setNovaEntrada((p) => ({ ...p, nota_fiscal: e.target.value }))}
                      placeholder="NF-e 00001..."
                    />
                    <div className="flex flex-col gap-1">
                      <label className="text-xs font-medium text-gray-600 dark:text-slate-400">Observacoes</label>
                      <textarea
                        value={novaEntrada.observacoes}
                        onChange={(e) => setNovaEntrada((p) => ({ ...p, observacoes: e.target.value }))}
                        rows={2}
                        className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500"
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={handleRegistrarEntrada} loading={savingEntrada}>
                        Confirmar
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => setNovaEntrada(null)}>
                        Cancelar
                      </Button>
                    </div>
                  </div>
                )}

                {loadingEntradas ? (
                  <p className="text-xs text-gray-400 dark:text-slate-500">Carregando entradas...</p>
                ) : entradas.length === 0 ? (
                  <p className="text-xs text-gray-400 dark:text-slate-500">Nenhuma entrada registrada.</p>
                ) : (
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {entradas.map((en, i) => (
                      <div key={en.id || i} className="flex items-center justify-between text-xs py-1 border-b border-gray-100 last:border-0 dark:border-navy-700">
                        <div className="min-w-0">
                          <span className="font-medium text-gray-700 dark:text-slate-300">{en.quantidade} {en.unidade}</span>
                          {en.nota_fiscal && <span className="text-gray-400 ml-1 dark:text-slate-500">({en.nota_fiscal})</span>}
                        </div>
                        <span className="text-gray-400 ml-2 shrink-0 dark:text-slate-500">
                          {en.created_at ? new Date(en.created_at).toLocaleDateString('pt-BR') : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Observacoes</label>
              <textarea
                name="observacoes"
                value={form.observacoes}
                onChange={handleChange}
                rows={3}
                placeholder="Informacoes adicionais..."
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500 transition-colors duration-150"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={closeModal}>
                Cancelar
              </Button>
              <Button type="submit" loading={saving}>
                {editingId ? 'Salvar Alteracoes' : 'Cadastrar Produto'}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

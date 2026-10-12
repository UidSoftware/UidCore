import { useState, useEffect, useCallback, useRef } from 'react'
import { Pencil, PauseCircle, PlayCircle, XCircle, Search, Trash2 } from 'lucide-react'
import api from '../api/client.js'
import { extractErrorMessage, stripEmptyStrings } from '../utils/errors.js'
import Card from '../components/ui/Card.jsx'
import Button from '../components/ui/Button.jsx'
import Input from '../components/ui/Input.jsx'
import Select from '../components/ui/Select.jsx'
import Modal from '../components/ui/Modal.jsx'
import Pagination from '../components/ui/Pagination.jsx'
import AuditFooter from '../components/ui/AuditFooter.jsx'

const PAGE_SIZE = 10

const BRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

// Mesma implementacao ja usada em Compras.jsx/Marketing.jsx — evita shift de
// fuso-horario que `new Date(d).toLocaleDateString()` introduziria para
// DateField (sem hora) vindos do backend no formato "aaaa-mm-dd".
function formatData(d) {
  if (!d) return '—'
  const [ano, mes, dia] = d.split('-')
  return `${dia}/${mes}/${ano}`
}

const STATUS_FILTRO_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'ATIVA', label: 'Ativa' },
  { value: 'PAUSADA', label: 'Pausada' },
  { value: 'ENCERRADA', label: 'Encerrada' },
]

// Badge de status de Assinatura — duplicado localmente (padrao do projeto,
// nao existe Badge/StatusBadge compartilhado). ATIVA reaproveita o verde de
// PAGO, PAUSADA o amarelo de PENDENTE, ENCERRADA o cinza de CANCELADO
// (mesmas classes de Compras.jsx).
const STATUS_BADGES = {
  ATIVA: 'bg-green-100 text-green-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  PAUSADA: 'bg-yellow-100 text-yellow-800 dark:bg-amber-900/30 dark:text-amber-300',
  ENCERRADA: 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400',
}

function Badge({ status }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${STATUS_BADGES[status] || STATUS_BADGES.ENCERRADA}`}>
      {status}
    </span>
  )
}

const EMPTY_FORM = {
  valor: '',
  dia_vencimento: '',
  data_inicio: '',
  data_fim: '',
  conta: '',
}

const EMPTY_PLANO_FORM = {
  nome: '',
  descricao: '',
  valor: '',
  periodicidade: 'MENSAL',
  categoria: '',
  ativo: true,
}

const PERIODICIDADE_OPTIONS = [
  { value: 'MENSAL', label: 'Mensal' },
  { value: 'TRIMESTRAL', label: 'Trimestral' },
  { value: 'SEMESTRAL', label: 'Semestral' },
  { value: 'ANUAL', label: 'Anual' },
]

// --- Autocomplete de cliente (mesmo padrao debounced ja usado em
// FrenteDeCaixa.jsx/Vendas.jsx — modal pequeno, sem position:fixed porque
// nao ha overflow-y-auto agressivo o suficiente pra justificar o truque de
// getBoundingClientRect() usado em ProdutoAutocomplete). ---
function ClienteAutocomplete({ clienteSelecionado, onSelecionar, onLimpar, disabled }) {
  const [busca, setBusca] = useState('')
  const [resultados, setResultados] = useState([])
  const [buscando, setBuscando] = useState(false)
  const debounceRef = useRef(null)
  const wrapRef = useRef(null)

  useEffect(() => {
    clearTimeout(debounceRef.current)
    if (!busca.trim()) {
      setResultados([])
      return
    }
    debounceRef.current = setTimeout(() => {
      setBuscando(true)
      api.get('/clientes/', { params: { search: busca.trim(), page_size: 10 } })
        .then((r) => setResultados(r.data.results || r.data || []))
        .catch(() => setResultados([]))
        .finally(() => setBuscando(false))
    }, 300)
    return () => clearTimeout(debounceRef.current)
  }, [busca])

  useEffect(() => {
    const handler = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setResultados([])
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  if (disabled) {
    return (
      <Input label="Cliente" value={clienteSelecionado?.nome || ''} disabled />
    )
  }

  if (clienteSelecionado) {
    return (
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Cliente</label>
        <div className="flex items-center justify-between rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm dark:border-navy-500 dark:bg-navy-900">
          <span className="text-gray-800 dark:text-slate-200 truncate">{clienteSelecionado.nome}</span>
          <button type="button" onClick={onLimpar} className="text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-300 shrink-0 ml-2">
            ✕
          </button>
        </div>
      </div>
    )
  }

  return (
    <div ref={wrapRef} className="relative flex flex-col gap-1">
      <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Cliente</label>
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-slate-500 pointer-events-none" />
        <input
          type="text"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar cliente por nome..."
          autoComplete="off"
          className="w-full rounded-lg border border-gray-300 bg-white pl-9 pr-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500"
        />
      </div>
      {(resultados.length > 0 || buscando) && (
        <div className="relative z-10 bg-white rounded-lg shadow-lg border border-gray-200 max-h-48 overflow-y-auto dark:bg-navy-800 dark:border-navy-600 dark:shadow-none">
          {buscando && (
            <div className="px-4 py-3 text-sm text-gray-400 dark:text-slate-500 text-center">Buscando...</div>
          )}
          {!buscando && resultados.map((c) => (
            <button
              key={c.id}
              type="button"
              onMouseDown={() => { onSelecionar(c); setBusca(''); setResultados([]) }}
              className="w-full text-left px-4 py-2.5 hover:bg-gray-50 border-b border-gray-100 last:border-0 transition-colors dark:hover:bg-navy-700 dark:border-navy-700"
            >
              <p className="text-sm font-medium text-gray-900 dark:text-slate-100">{c.nome_razao_social}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Assinaturas() {
  const [abaPrincipal, setAbaPrincipal] = useState('assinaturas')
  const [toast, setToast] = useState(null)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), type === 'error' ? 7000 : 3500)
  }

  return (
    <div className="space-y-4">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white whitespace-pre-line break-words ${toast.type === 'error' ? 'bg-red-600' : 'bg-accent-600'}`}>
          {toast.msg}
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Assinaturas</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-0.5">
            Mensalidades recorrentes — planos, contratos ativos e cobrança automática
          </p>
        </div>
      </div>

      <div className="flex gap-1 border-b border-gray-200 dark:border-navy-600">
        <button
          onClick={() => setAbaPrincipal('assinaturas')}
          className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
            abaPrincipal === 'assinaturas'
              ? 'border-violet-500 text-violet-600 dark:text-violet-400'
              : 'border-transparent text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300'
          }`}
        >
          Assinaturas
        </button>
        <button
          onClick={() => setAbaPrincipal('planos')}
          className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
            abaPrincipal === 'planos'
              ? 'border-violet-500 text-violet-600 dark:text-violet-400'
              : 'border-transparent text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300'
          }`}
        >
          Planos
        </button>
      </div>

      {abaPrincipal === 'assinaturas' ? (
        <AbaListaAssinaturas showToast={showToast} />
      ) : (
        <AbaListaPlanos showToast={showToast} />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Aba Assinaturas — listagem principal (RF-10)
// ---------------------------------------------------------------------------
function AbaListaAssinaturas({ showToast }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [statusFiltro, setStatusFiltro] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [editingId, setEditingId] = useState(null)
  const [editingItem, setEditingItem] = useState(null)
  const [clienteSelecionado, setClienteSelecionado] = useState(null)
  const [planoSelecionado, setPlanoSelecionado] = useState('')
  const [planoNomeSelecionado, setPlanoNomeSelecionado] = useState('')

  const [planoOptions, setPlanoOptions] = useState([])
  const [contasOptions, setContasOptions] = useState([])

  const [encerrarItem, setEncerrarItem] = useState(null)
  const [encerrarForm, setEncerrarForm] = useState({ data_fim: '', motivo: '' })
  const [encerrando, setEncerrando] = useState(false)

  useEffect(() => {
    api.get('/assinaturas/planos/', { params: { ativo: true, page_size: 200 } })
      .then((r) => setPlanoOptions(r.data.results || r.data || []))
      .catch(() => {})

    api.get('/financeiro/contas/', { params: { page_size: 200 } })
      .then((r) => {
        const list = (r.data.results || r.data || []).map((c) => ({ value: c.id, label: c.nome }))
        setContasOptions([{ value: '', label: 'Selecione...' }, ...list])
      })
      .catch(() => {})
  }, [])

  const fetchItems = useCallback(async () => {
    setLoading(true)
    try {
      const params = { search, page, page_size: PAGE_SIZE }
      if (statusFiltro) params.status = statusFiltro
      const r = await api.get('/assinaturas/assinaturas/', { params })
      setItems(r.data.results || r.data || [])
      const count = r.data.count ?? (r.data.results || r.data || []).length
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
    } catch {
      showToast('Erro ao carregar assinaturas.', 'error')
    } finally {
      setLoading(false)
    }
  }, [search, statusFiltro, page, showToast])

  useEffect(() => { fetchItems() }, [fetchItems])

  const openNovaAssinatura = () => {
    setForm(EMPTY_FORM)
    setEditingId(null)
    setEditingItem(null)
    setClienteSelecionado(null)
    setPlanoSelecionado('')
    setPlanoNomeSelecionado('')
    setModalOpen(true)
  }

  const openEditar = (item) => {
    setForm({
      valor: item.valor ?? '',
      dia_vencimento: item.dia_vencimento ?? '',
      data_inicio: item.data_inicio ?? '',
      data_fim: item.data_fim ?? '',
      conta: item.conta ?? '',
    })
    setEditingId(item.id)
    setEditingItem(item)
    setClienteSelecionado({ id: item.cliente, nome: item.cliente_nome })
    setPlanoSelecionado(item.plano)
    setPlanoNomeSelecionado(item.plano_nome)
    setModalOpen(true)
  }

  const closeModal = () => {
    setModalOpen(false)
    setForm(EMPTY_FORM)
    setEditingId(null)
    setEditingItem(null)
    setClienteSelecionado(null)
    setPlanoSelecionado('')
    setPlanoNomeSelecionado('')
  }

  const handleChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }))

  const handleSelecionarPlano = (e) => {
    const id = e.target.value
    setPlanoSelecionado(id)
    const plano = planoOptions.find((p) => String(p.id) === String(id))
    if (plano) {
      setForm((p) => ({ ...p, valor: plano.valor }))
    }
  }

  const handleSubmit = async () => {
    if (!editingId && (!clienteSelecionado || !planoSelecionado)) {
      showToast('Selecione o cliente e o plano.', 'error')
      return
    }
    setSaving(true)
    try {
      const payload = stripEmptyStrings({
        valor: form.valor,
        dia_vencimento: form.dia_vencimento,
        data_inicio: form.data_inicio,
        data_fim: form.data_fim,
        conta: form.conta,
      })
      if (editingId) {
        await api.patch(`/assinaturas/assinaturas/${editingId}/`, payload)
        showToast('Assinatura atualizada.')
      } else {
        payload.cliente = clienteSelecionado.id
        payload.plano = planoSelecionado
        await api.post('/assinaturas/assinaturas/', payload)
        showToast('Assinatura cadastrada.')
      }
      closeModal()
      fetchItems()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao salvar assinatura.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const togglePausarRetomar = async (item) => {
    try {
      const acao = item.status === 'ATIVA' ? 'pausar' : 'retomar'
      await api.post(`/assinaturas/assinaturas/${item.id}/${acao}/`)
      showToast(acao === 'pausar' ? 'Assinatura pausada.' : 'Assinatura retomada.')
      fetchItems()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao atualizar assinatura.'), 'error')
    }
  }

  const abrirModalEncerrar = (item) => {
    setEncerrarItem(item)
    setEncerrarForm({ data_fim: '', motivo: '' })
  }

  const fecharModalEncerrar = () => {
    setEncerrarItem(null)
    setEncerrarForm({ data_fim: '', motivo: '' })
  }

  const confirmarEncerramento = async () => {
    if (!encerrarForm.data_fim) {
      showToast('Informe a data de encerramento.', 'error')
      return
    }
    setEncerrando(true)
    try {
      await api.post(`/assinaturas/assinaturas/${encerrarItem.id}/encerrar/`, {
        data_fim: encerrarForm.data_fim,
        motivo: encerrarForm.motivo,
      })
      showToast('Assinatura encerrada.')
      fecharModalEncerrar()
      fetchItems()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao encerrar assinatura.'), 'error')
    } finally {
      setEncerrando(false)
    }
  }

  return (
    <>
      <div className="flex items-center justify-end">
        <Button onClick={openNovaAssinatura}>+ Nova Assinatura</Button>
      </div>

      <Card>
        <div className="flex flex-wrap gap-3">
          <div className="flex-1 min-w-[200px]">
            <Input
              placeholder="Buscar por cliente..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            />
          </div>
          <div className="w-48">
            <Select
              options={STATUS_FILTRO_OPTIONS}
              value={statusFiltro}
              onChange={(e) => { setStatusFiltro(e.target.value); setPage(1) }}
            />
          </div>
        </div>
      </Card>

      {loading ? (
        <div className="text-center py-12 text-gray-400 dark:text-slate-500 text-sm">Carregando...</div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400 dark:text-slate-500">
          <span className="text-4xl">🔁</span>
          <p className="text-sm">Nenhuma assinatura cadastrada.</p>
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-3 md:hidden">
            {items.map((item) => (
              <Card key={item.id}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-medium text-gray-800 dark:text-slate-200 truncate">{item.cliente_nome}</p>
                    <p className="text-xs text-gray-400 dark:text-slate-500">
                      {item.plano_nome} · vence dia {item.dia_vencimento}
                    </p>
                  </div>
                  <Badge status={item.status} />
                </div>
                <div className="flex items-center justify-between mt-2">
                  <span className="font-semibold text-gray-800 dark:text-slate-200">{BRL(item.valor)}</span>
                  <div className="flex gap-3">
                    <button onClick={() => openEditar(item)} className="text-gray-400 dark:text-slate-500">
                      <Pencil size={16} />
                    </button>
                    {item.status !== 'ENCERRADA' && (
                      <button onClick={() => togglePausarRetomar(item)} className="text-gray-400 dark:text-slate-500">
                        {item.status === 'ATIVA' ? <PauseCircle size={16} /> : <PlayCircle size={16} />}
                      </button>
                    )}
                    {item.status !== 'ENCERRADA' && (
                      <button onClick={() => abrirModalEncerrar(item)} className="text-gray-400 dark:text-slate-500">
                        <XCircle size={16} />
                      </button>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>

          <div className="hidden md:block">
            <Card>
              <div className="overflow-x-auto -mx-6 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200 dark:bg-navy-900 dark:border-navy-600">
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Cliente</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Plano</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Valor</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Vencimento</th>
                      <th className="text-center px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Status</th>
                      <th className="text-center px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-navy-700">
                    {items.map((item) => (
                      <tr key={item.id} className="border-b border-gray-100 dark:border-navy-700 hover:bg-gray-50 dark:hover:bg-navy-700/30">
                        <td className="px-4 py-3 font-medium text-gray-900 dark:text-slate-100">{item.cliente_nome}</td>
                        <td className="px-4 py-3 text-gray-600 dark:text-slate-400">{item.plano_nome}</td>
                        <td className="px-4 py-3 text-right font-medium text-gray-900 dark:text-slate-100">{BRL(item.valor)}</td>
                        <td className="px-4 py-3 text-gray-600 dark:text-slate-400">dia {item.dia_vencimento}</td>
                        <td className="px-4 py-3 text-center"><Badge status={item.status} /></td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex justify-center gap-3">
                            <button onClick={() => openEditar(item)} title="Editar"
                              className="text-gray-400 hover:text-primary-600 transition-colors dark:text-slate-500 dark:hover:text-violet-400">
                              <Pencil size={16} />
                            </button>
                            {item.status !== 'ENCERRADA' && (
                              <button onClick={() => togglePausarRetomar(item)} title={item.status === 'ATIVA' ? 'Pausar' : 'Retomar'}
                                className="text-gray-400 hover:text-primary-600 transition-colors dark:text-slate-500 dark:hover:text-violet-400">
                                {item.status === 'ATIVA' ? <PauseCircle size={16} /> : <PlayCircle size={16} />}
                              </button>
                            )}
                            {item.status !== 'ENCERRADA' && (
                              <button onClick={() => abrirModalEncerrar(item)} title="Encerrar"
                                className="text-gray-400 hover:text-red-600 transition-colors dark:text-slate-500 dark:hover:text-red-400">
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

      {/* Modal Nova/Editar Assinatura */}
      {modalOpen && (
        <Modal title={editingId ? 'Editar Assinatura' : 'Nova Assinatura'} onClose={closeModal} maxW="max-w-lg">
          <div className="space-y-4">
            <ClienteAutocomplete
              clienteSelecionado={clienteSelecionado}
              onSelecionar={(c) => setClienteSelecionado({ id: c.id, nome: c.nome_razao_social })}
              onLimpar={() => setClienteSelecionado(null)}
              disabled={!!editingId}
            />

            {editingId ? (
              <Input label="Plano" value={planoNomeSelecionado} disabled />
            ) : (
              <Select
                label="Plano"
                options={[{ value: '', label: 'Selecione...' }, ...planoOptions.map((p) => ({ value: p.id, label: `${p.nome} — ${BRL(p.valor)}` }))]}
                value={planoSelecionado}
                onChange={handleSelecionarPlano}
              />
            )}

            <Input label="Valor (R$)" name="valor" type="number" step="0.01" min="0" value={form.valor} onChange={handleChange} />

            <div className="flex flex-col gap-1">
              <Input label="Dia do vencimento" name="dia_vencimento" type="number" min={1} max={28} value={form.dia_vencimento} onChange={handleChange} />
              <p className="text-xs text-gray-400 dark:text-slate-500">Entre 1 e 28 — evita problema em meses com menos dias</p>
            </div>

            <Input label="Início" name="data_inicio" type="date" value={form.data_inicio} onChange={handleChange} />

            <div className="flex flex-col gap-1">
              <Input label="Fim (opcional)" name="data_fim" type="date" value={form.data_fim} onChange={handleChange} />
              <p className="text-xs text-gray-400 dark:text-slate-500">Deixe em branco para contrato sem prazo definido</p>
            </div>

            <Select label="Conta de destino" name="conta" options={contasOptions} value={form.conta} onChange={handleChange} />

            {editingId && <AuditFooter item={editingItem} />}

            <div className="flex justify-end gap-2 mt-5">
              <Button variant="secondary" onClick={closeModal}>Cancelar</Button>
              <Button onClick={handleSubmit} loading={saving} disabled={saving}>
                {saving ? 'Salvando...' : 'Salvar'}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal Encerrar Assinatura — acao sem volta, fricção visual proposital (RN-07) */}
      {encerrarItem && (
        <Modal title="Encerrar Assinatura" onClose={fecharModalEncerrar} maxW="max-w-sm">
          <div className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-slate-300">
              Encerrar a assinatura de {encerrarItem.cliente_nome}? Essa ação não pode ser
              desfeita — a assinatura para de gerar cobrança a partir da data informada.
            </p>

            <Input
              label="A partir de"
              type="date"
              value={encerrarForm.data_fim}
              onChange={(e) => setEncerrarForm((p) => ({ ...p, data_fim: e.target.value }))}
            />

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Motivo do encerramento</label>
              <textarea
                rows={3}
                value={encerrarForm.motivo}
                onChange={(e) => setEncerrarForm((p) => ({ ...p, motivo: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500"
              />
            </div>

            <div className="flex justify-end gap-2 mt-5">
              <Button variant="secondary" onClick={fecharModalEncerrar}>Cancelar</Button>
              <Button
                onClick={confirmarEncerramento}
                loading={encerrando}
                disabled={encerrando}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                {encerrando ? 'Encerrando...' : 'Confirmar encerramento'}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  )
}

// ---------------------------------------------------------------------------
// Aba Planos — CRUD simples (RF-02, RNF-02) — a Especificacao_Hotfix.md pede
// criar/editar/excluir plano no frontend; segue o mesmo padrao de Card+Modal
// ja usado em Assinaturas, sem componente novo.
// ---------------------------------------------------------------------------
function AbaListaPlanos({ showToast }) {
  const [planos, setPlanos] = useState([])
  const [loading, setLoading] = useState(false)
  const [categoriaOptions, setCategoriaOptions] = useState([])

  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(EMPTY_PLANO_FORM)
  const [editingId, setEditingId] = useState(null)

  const fetchPlanos = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.get('/assinaturas/planos/', { params: { page_size: 200 } })
      setPlanos(r.data.results || r.data || [])
    } catch {
      showToast('Erro ao carregar planos.', 'error')
    } finally {
      setLoading(false)
    }
  }, [showToast])

  useEffect(() => { fetchPlanos() }, [fetchPlanos])

  useEffect(() => {
    api.get('/financeiro/categorias/', { params: { tipo: 'ENTRADA', page_size: 200 } })
      .then((r) => {
        const list = (r.data.results || r.data || []).map((c) => ({ value: c.id, label: c.nome }))
        setCategoriaOptions([{ value: '', label: 'Selecione...' }, ...list])
      })
      .catch(() => {})
  }, [])

  const openNovo = () => {
    setForm(EMPTY_PLANO_FORM)
    setEditingId(null)
    setModalOpen(true)
  }

  const openEditar = (plano) => {
    setForm({
      nome: plano.nome || '',
      descricao: plano.descricao || '',
      valor: plano.valor ?? '',
      periodicidade: plano.periodicidade || 'MENSAL',
      categoria: plano.categoria ?? '',
      ativo: plano.ativo,
    })
    setEditingId(plano.id)
    setModalOpen(true)
  }

  const closeModal = () => {
    setModalOpen(false)
    setForm(EMPTY_PLANO_FORM)
    setEditingId(null)
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((p) => ({ ...p, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleSubmit = async () => {
    setSaving(true)
    try {
      const payload = stripEmptyStrings({
        nome: form.nome,
        descricao: form.descricao,
        valor: form.valor,
        periodicidade: form.periodicidade,
        categoria: form.categoria,
      })
      payload.ativo = form.ativo
      if (editingId) {
        await api.patch(`/assinaturas/planos/${editingId}/`, payload)
        showToast('Plano atualizado.')
      } else {
        await api.post('/assinaturas/planos/', payload)
        showToast('Plano cadastrado.')
      }
      closeModal()
      fetchPlanos()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao salvar plano.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleExcluir = async (plano) => {
    if (!window.confirm(`Excluir o plano "${plano.nome}"?`)) return
    try {
      await api.delete(`/assinaturas/planos/${plano.id}/`)
      showToast('Plano removido.')
      fetchPlanos()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao remover plano.'), 'error')
    }
  }

  return (
    <>
      <div className="flex items-center justify-end">
        <Button onClick={openNovo}>+ Novo Plano</Button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400 dark:text-slate-500 text-sm">Carregando...</div>
      ) : planos.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400 dark:text-slate-500">
          <span className="text-4xl">🔁</span>
          <p className="text-sm">Nenhum plano cadastrado.</p>
        </div>
      ) : (
        <Card>
          <div className="divide-y divide-gray-100 dark:divide-navy-700">
            {planos.map((plano) => (
              <div key={plano.id} className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                <div className="min-w-0">
                  <p className="font-medium text-gray-800 dark:text-slate-200 truncate">{plano.nome}</p>
                  <p className="text-xs text-gray-400 dark:text-slate-500">
                    {BRL(plano.valor)} · {PERIODICIDADE_OPTIONS.find((o) => o.value === plano.periodicidade)?.label || plano.periodicidade} · {plano.categoria_nome}
                  </p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${plano.ativo ? 'bg-green-100 text-green-800 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400'}`}>
                    {plano.ativo ? 'Ativo' : 'Inativo'}
                  </span>
                  <button onClick={() => openEditar(plano)} title="Editar"
                    className="text-gray-400 hover:text-primary-600 transition-colors dark:text-slate-500 dark:hover:text-violet-400">
                    <Pencil size={16} />
                  </button>
                  <button onClick={() => handleExcluir(plano)} title="Excluir"
                    className="text-gray-400 hover:text-red-600 transition-colors dark:text-slate-500 dark:hover:text-red-400">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {modalOpen && (
        <Modal title={editingId ? 'Editar Plano' : 'Novo Plano'} onClose={closeModal} maxW="max-w-lg">
          <div className="space-y-4">
            <Input label="Nome" name="nome" value={form.nome} onChange={handleChange} placeholder="Ex.: Plano Mensal Básico" />
            <Input label="Valor (R$)" name="valor" type="number" step="0.01" min="0" value={form.valor} onChange={handleChange} />
            <Select label="Periodicidade" name="periodicidade" options={PERIODICIDADE_OPTIONS} value={form.periodicidade} onChange={handleChange} />
            <Select label="Categoria" name="categoria" options={categoriaOptions} value={form.categoria} onChange={handleChange} />
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Descrição</label>
              <textarea
                name="descricao"
                rows={2}
                value={form.descricao}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300 cursor-pointer">
              <input type="checkbox" name="ativo" checked={!!form.ativo} onChange={handleChange} className="accent-primary-600 dark:accent-violet-600" />
              Disponível para novas assinaturas
            </label>

            <div className="flex justify-end gap-2 mt-5">
              <Button variant="secondary" onClick={closeModal}>Cancelar</Button>
              <Button onClick={handleSubmit} loading={saving} disabled={saving}>
                {saving ? 'Salvando...' : 'Salvar'}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  )
}

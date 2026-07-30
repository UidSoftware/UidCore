import { useState, useEffect, useCallback } from 'react'
import {
  Plus, Upload, ChevronRight, Inbox, CheckCircle2, AlertTriangle,
  ArrowUpCircle, ArrowDownCircle,
} from 'lucide-react'
import api from '../api/client.js'
import { extractErrorMessage, stripEmptyStrings } from '../utils/errors.js'
import Card from '../components/ui/Card.jsx'
import Button from '../components/ui/Button.jsx'
import Input from '../components/ui/Input.jsx'
import Select from '../components/ui/Select.jsx'
import Modal from '../components/ui/Modal.jsx'
import Pagination from '../components/ui/Pagination.jsx'

const PAGE_SIZE = 20

const TABS = [
  { key: 'historico', label: 'Histórico' },
  { key: 'padroes', label: 'Padrões Seguros' },
]

// StatusConciliacao (backend financeiro/models.py)
const STATUS_CONCILIACAO_BADGES = {
  PROCESSADO: 'bg-green-100 text-green-800',
  COM_DIVERGENCIAS: 'bg-red-100 text-red-800',
  PENDENTE: 'bg-yellow-100 text-yellow-800',
}
const STATUS_CONCILIACAO_LABELS = {
  PROCESSADO: 'Processado',
  COM_DIVERGENCIAS: 'Com Divergências',
  PENDENTE: 'Pendente',
}

// StatusItemConciliacao (backend financeiro/models.py)
const STATUS_ITEM_BADGES = {
  CONCILIADO: 'bg-green-100 text-green-800',
  FALTANDO_BANCO: 'bg-yellow-100 text-yellow-800',
  FALTANDO_SISTEMA: 'bg-red-100 text-red-800',
}
const STATUS_ITEM_LABELS = {
  CONCILIADO: 'Conciliado',
  FALTANDO_SISTEMA: 'Faltando no Sistema',
  FALTANDO_BANCO: 'Faltando no Banco',
}

const TIPO_ITEM_OPTIONS = [
  { value: 'ENTRADA', label: 'Entrada' },
  { value: 'SAIDA', label: 'Saída' },
]

const NATUREZA_OPTIONS = [
  { value: 'APORTE', label: 'Aporte' },
  { value: 'RECEITA_FINANCEIRA', label: 'Receita Financeira' },
]

const BRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

function formatarPeriodo(periodo) {
  if (!periodo) return '—'
  const [ano, mes] = periodo.split('-')
  return mes ? `${mes}/${ano}` : periodo
}

function formatarData(data) {
  if (!data) return '—'
  const [ano, mes, dia] = data.split('-')
  return dia ? `${dia}/${mes}/${ano}` : data
}

function formatarDataHora(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function Badge({ status, map, labels }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${map[status] || 'bg-gray-100 text-gray-600'}`}>
      {labels[status] || status}
    </span>
  )
}

export default function Conciliacao() {
  const [tab, setTab] = useState('historico')
  const [toast, setToast] = useState(null)
  const [contasOptions, setContasOptions] = useState([])

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), type === 'error' ? 7000 : 3500)
  }

  useEffect(() => {
    api.get('/financeiro/contas/').then((r) => {
      const list = (r.data.results || r.data || []).map((c) => ({
        value: c.id, label: c.nome,
      }))
      setContasOptions(list)
    }).catch(() => {})
  }, [])

  return (
    <div className="space-y-4">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white whitespace-pre-line break-words ${toast.type === 'error' ? 'bg-red-600' : 'bg-accent-600'}`}>
          {toast.msg}
        </div>
      )}

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Conciliação Bancária</h1>
        <p className="text-sm text-gray-500 mt-0.5">Envie extratos e concilie com o Livro Caixa</p>
      </div>

      <div className="flex gap-1 overflow-x-auto pb-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium rounded-lg whitespace-nowrap transition-colors ${
              tab === t.key
                ? 'bg-primary-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'historico' && <HistoricoTab showToast={showToast} contasOptions={contasOptions} />}
      {tab === 'padroes' && <PadroesTab showToast={showToast} />}
    </div>
  )
}

const EMPTY_UPLOAD = { conta_id: '', periodo: '', senha: '', auto: false }

function HistoricoTab({ showToast, contasOptions }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [form, setForm] = useState(EMPTY_UPLOAD)
  const [arquivo, setArquivo] = useState(null)
  const [selecionada, setSelecionada] = useState(null)

  const fetchItems = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.get('/financeiro/conciliacoes/', { params: { page, page_size: PAGE_SIZE } })
      setItems(r.data.results || r.data || [])
      const count = r.data.count || (r.data.results || r.data || []).length
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
    } catch {
      showToast('Erro ao carregar conciliações.', 'error')
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => { fetchItems() }, [fetchItems])

  const openNovaConciliacao = () => { setForm(EMPTY_UPLOAD); setArquivo(null); setModalOpen(true) }
  const closeModal = () => setModalOpen(false)

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((p) => ({ ...p, [name]: value }))
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!arquivo || !form.conta_id || !form.periodo) {
      showToast('Arquivo, conta e período são obrigatórios.', 'error')
      return
    }
    setUploading(true)
    try {
      const data = new FormData()
      data.append('arquivo', arquivo)
      data.append('conta_id', form.conta_id.toString())
      data.append('periodo', form.periodo)
      if (form.senha) data.append('senha', form.senha)
      data.append('auto', form.auto ? 'true' : 'false')

      await api.post('/financeiro/conciliacoes/upload/', data, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      showToast('Extrato enviado e conciliação processada.')
      closeModal()
      fetchItems()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao enviar extrato.'), 'error')
    } finally {
      setUploading(false)
    }
  }

  const abrirDetalhe = (item) => setSelecionada(item)
  const fecharDetalhe = () => setSelecionada(null)

  const atualizarNaLista = (patch) => {
    setItems((prev) => prev.map((it) => (it.id === patch.id ? { ...it, ...patch } : it)))
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-800">Histórico de Conciliações</h2>
        <Button onClick={openNovaConciliacao}>
          <Plus size={16} className="mr-1" /> Nova Conciliação
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400 text-sm">Carregando...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <Inbox size={40} className="mx-auto mb-2 opacity-50" />
          <p className="text-sm">Nenhuma conciliação enviada ainda.</p>
        </div>
      ) : (
        <>
          {/* Mobile */}
          <div className="flex flex-col gap-3 md:hidden">
            {items.map((item) => (
              <div key={item.id} className="cursor-pointer" onClick={() => abrirDetalhe(item)}>
                <Card>
                  <div className="flex justify-between items-start gap-2">
                    <div className="min-w-0">
                      <p className="font-semibold text-gray-900 truncate">{item.conta_nome}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{formatarPeriodo(item.periodo)}</p>
                    </div>
                    <Badge status={item.status} map={STATUS_CONCILIACAO_BADGES} labels={STATUS_CONCILIACAO_LABELS} />
                  </div>
                  <div className="mt-2 flex justify-between items-center text-sm">
                    <span className="text-gray-500">Banco: <span className="font-mono text-gray-700">{BRL(item.total_banco)}</span></span>
                    <span className="text-gray-500">Sistema: <span className="font-mono text-gray-700">{BRL(item.total_sistema)}</span></span>
                  </div>
                  {item.divergencias > 0 && (
                    <p className="text-xs text-red-600 font-medium mt-1">{item.divergencias} divergência(s)</p>
                  )}
                </Card>
              </div>
            ))}
          </div>

          {/* Desktop */}
          <div className="hidden md:block">
            <Card>
              <div className="overflow-x-auto -mx-6 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Período</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Conta</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Status</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600">Total Banco</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600">Total Sistema</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600">Divergências</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Processado em</th>
                      <th className="px-4 py-3" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {items.map((item) => (
                      <tr key={item.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => abrirDetalhe(item)}>
                        <td className="px-4 py-3 text-gray-600">{formatarPeriodo(item.periodo)}</td>
                        <td className="px-4 py-3 text-gray-600">{item.conta_nome}</td>
                        <td className="px-4 py-3">
                          <Badge status={item.status} map={STATUS_CONCILIACAO_BADGES} labels={STATUS_CONCILIACAO_LABELS} />
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-gray-700">{BRL(item.total_banco)}</td>
                        <td className="px-4 py-3 text-right font-mono text-gray-700">{BRL(item.total_sistema)}</td>
                        <td className={`px-4 py-3 text-right ${item.divergencias > 0 ? 'font-semibold text-red-600' : 'text-gray-400'}`}>
                          {item.divergencias}
                        </td>
                        <td className="px-4 py-3 text-gray-500 text-xs">{formatarDataHora(item.processado_em)}</td>
                        <td className="px-4 py-3 text-right"><ChevronRight size={16} className="text-gray-400" /></td>
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

      {modalOpen && (
        <Modal title="Nova Conciliação" onClose={closeModal} maxW="max-w-lg">
          <form onSubmit={handleUpload} className="space-y-4">
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700">Extrato Bancário (PDF)</label>
              <input
                type="file"
                accept="application/pdf"
                required
                onChange={(e) => setArquivo(e.target.files?.[0] || null)}
                className="w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-primary-50 file:text-primary-700 file:text-sm file:font-medium hover:file:bg-primary-100"
              />
            </div>

            <Select
              label="Conta"
              name="conta_id"
              options={[{ value: '', label: 'Selecione...' }, ...contasOptions]}
              value={form.conta_id}
              onChange={handleChange}
              required
            />

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700">Período</label>
              <input
                type="month"
                name="periodo"
                required
                value={form.periodo}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors duration-150"
              />
            </div>

            <Input label="Senha do PDF (se protegido)" name="senha" type="password" value={form.senha} onChange={handleChange} />

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="auto"
                checked={form.auto}
                onChange={(e) => setForm((p) => ({ ...p, auto: e.target.checked }))}
                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <label htmlFor="auto" className="text-sm font-medium text-gray-700">
                Conciliar automaticamente por padrões seguros
              </label>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={closeModal}>Cancelar</Button>
              <Button type="submit" loading={uploading}>
                <Upload size={16} className="mr-1" /> Enviar Extrato
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {selecionada && (
        <DetalheConciliacao
          conciliacao={selecionada}
          onClose={fecharDetalhe}
          showToast={showToast}
          onAtualizar={atualizarNaLista}
        />
      )}
    </div>
  )
}

function DetalheConciliacao({ conciliacao, onClose, showToast, onAtualizar }) {
  const [itens, setItens] = useState([])
  const [loading, setLoading] = useState(true)
  const [confirmandoId, setConfirmandoId] = useState(null)
  const [status, setStatus] = useState(conciliacao.status)
  const [divergencias, setDivergencias] = useState(conciliacao.divergencias)

  const fetchItens = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.get(`/financeiro/conciliacoes/${conciliacao.id}/itens/`)
      setItens(r.data || [])
    } catch {
      showToast('Erro ao carregar itens da conciliação.', 'error')
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conciliacao.id])

  useEffect(() => { fetchItens() }, [fetchItens])

  const confirmarItem = async (item) => {
    setConfirmandoId(item.id)
    try {
      const r = await api.post(`/financeiro/conciliacoes/${conciliacao.id}/confirmar-item/`, { item_id: item.id })
      const restantes = r.data.divergencias_restantes
      const novoStatus = restantes === 0 ? 'PROCESSADO' : 'COM_DIVERGENCIAS'
      setItens((prev) => prev.map((it) => (it.id === item.id ? { ...it, confirmado: true } : it)))
      setDivergencias(restantes)
      setStatus(novoStatus)
      onAtualizar({ id: conciliacao.id, divergencias: restantes, status: novoStatus })
      showToast(`Item confirmado. ${restantes} divergência(s) restante(s).`)
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao confirmar item.'), 'error')
    } finally {
      setConfirmandoId(null)
    }
  }

  const linhaClasse = (item) => {
    if (item.status === 'FALTANDO_BANCO') return 'bg-yellow-50'
    if (item.status === 'FALTANDO_SISTEMA' && !item.confirmado) return 'bg-red-50'
    return 'hover:bg-gray-50'
  }

  return (
    <Modal title="Detalhe da Conciliação" onClose={onClose} maxW="max-w-4xl">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <div>
          <p className="text-xs text-gray-500">Conta</p>
          <p className="text-sm font-semibold text-gray-900">{conciliacao.conta_nome}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Período</p>
          <p className="text-sm font-semibold text-gray-900">{formatarPeriodo(conciliacao.periodo)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Status</p>
          <Badge status={status} map={STATUS_CONCILIACAO_BADGES} labels={STATUS_CONCILIACAO_LABELS} />
        </div>
        <div>
          <p className="text-xs text-gray-500">Divergências</p>
          <p className={`text-sm font-bold ${divergencias > 0 ? 'text-red-600' : 'text-green-600'}`}>{divergencias}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4 pb-4 border-b border-gray-100">
        <div className="rounded-xl p-3 bg-blue-50 text-blue-700">
          <p className="text-xs font-medium opacity-70">Total Banco</p>
          <p className="text-base font-bold mt-0.5">{BRL(conciliacao.total_banco)}</p>
        </div>
        <div className="rounded-xl p-3 bg-blue-50 text-blue-700">
          <p className="text-xs font-medium opacity-70">Total Sistema</p>
          <p className="text-base font-bold mt-0.5">{BRL(conciliacao.total_sistema)}</p>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400 text-sm">Carregando...</div>
      ) : itens.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <Inbox size={32} className="mx-auto mb-2 opacity-40" />
          <p className="text-sm">Nenhum item nesta conciliação.</p>
        </div>
      ) : (
        <div className="overflow-x-auto -mx-6">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Data</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Descrição</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Tipo</th>
                <th className="text-right px-4 py-3 font-semibold text-gray-600">Valor</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-600">Status</th>
                <th className="text-right px-4 py-3 font-semibold text-gray-600">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {itens.map((item) => (
                <tr key={item.id} className={linhaClasse(item)}>
                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{formatarData(item.data_banco)}</td>
                  <td className="px-4 py-3 text-gray-900 max-w-[220px] truncate">{item.descricao_banco}</td>
                  <td className="px-4 py-3">
                    <span className={`flex items-center gap-1 text-xs font-medium ${item.tipo === 'ENTRADA' ? 'text-green-700' : 'text-red-700'}`}>
                      {item.tipo === 'ENTRADA'
                        ? <ArrowUpCircle size={14} />
                        : <ArrowDownCircle size={14} />}
                      {item.tipo_label}
                    </span>
                  </td>
                  <td className={`px-4 py-3 text-right font-semibold whitespace-nowrap ${item.tipo === 'ENTRADA' ? 'text-green-700' : 'text-red-700'}`}>
                    {item.tipo === 'ENTRADA' ? '+' : '-'}{BRL(item.valor)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <Badge status={item.status} map={STATUS_ITEM_BADGES} labels={STATUS_ITEM_LABELS} />
                      {item.status === 'FALTANDO_BANCO' && <AlertTriangle size={14} className="text-yellow-600" />}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {item.status === 'FALTANDO_SISTEMA' && !item.confirmado && (
                      <Button size="sm" loading={confirmandoId === item.id} onClick={() => confirmarItem(item)}>
                        <CheckCircle2 size={14} className="mr-1" /> Confirmar
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  )
}

const EMPTY_PADRAO = { descricao_padrao: '', tipo: 'ENTRADA', natureza: 'APORTE' }

function PadroesTab({ showToast }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(EMPTY_PADRAO)

  const fetchItems = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.get('/financeiro/padroes-conciliacao/', { params: { page, page_size: PAGE_SIZE } })
      setItems(r.data.results || r.data || [])
      const count = r.data.count || (r.data.results || r.data || []).length
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
    } catch {
      showToast('Erro ao carregar padrões seguros.', 'error')
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => { fetchItems() }, [fetchItems])

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((p) => ({
      ...p,
      [name]: value,
      ...(name === 'tipo' && value === 'SAIDA' ? { natureza: 'APORTE' } : {}),
    }))
  }

  const openNew = () => { setForm(EMPTY_PADRAO); setEditingId(null); setModalOpen(true) }
  const openEdit = (item) => {
    setForm({
      descricao_padrao: item.descricao_padrao || '',
      tipo: item.tipo || 'ENTRADA',
      natureza: item.natureza || 'APORTE',
    })
    setEditingId(item.id); setModalOpen(true)
  }
  const closeModal = () => { setModalOpen(false); setEditingId(null) }

  const handleSubmit = async (e) => {
    e.preventDefault(); setSaving(true)
    try {
      const payload = stripEmptyStrings(form)
      if (editingId) {
        await api.patch(`/financeiro/padroes-conciliacao/${editingId}/`, payload)
        showToast('Padrão seguro atualizado.')
      } else {
        await api.post('/financeiro/padroes-conciliacao/', payload)
        showToast('Padrão seguro cadastrado.')
      }
      closeModal(); fetchItems()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao salvar padrão seguro.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (item) => {
    if (!window.confirm(`Excluir o padrão "${item.descricao_padrao}"?`)) return
    try {
      await api.delete(`/financeiro/padroes-conciliacao/${item.id}/`)
      showToast('Padrão seguro removido.')
      fetchItems()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao remover padrão seguro.'), 'error')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-800">Padrões Seguros</h2>
        <Button onClick={openNew}>
          <Plus size={16} className="mr-1" /> Novo Padrão
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400 text-sm">Carregando...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <Inbox size={40} className="mx-auto mb-2 opacity-50" />
          <p className="text-sm">Nenhum padrão seguro cadastrado.</p>
        </div>
      ) : (
        <>
          <Card>
            <div className="overflow-x-auto -mx-6 -my-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Descrição</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Tipo</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Natureza</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-600">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {items.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900 max-w-[280px] truncate">{item.descricao_padrao}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${item.tipo === 'ENTRADA' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                          {item.tipo_label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600">
                        {item.tipo === 'ENTRADA' ? item.natureza_label : <span className="text-gray-400">—</span>}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button size="sm" variant="secondary" onClick={() => openEdit(item)}>Editar</Button>
                          <Button size="sm" variant="danger" onClick={() => handleDelete(item)}>Excluir</Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}

      {modalOpen && (
        <Modal title={editingId ? 'Editar Padrão' : 'Novo Padrão'} onClose={closeModal}>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label="Descrição" name="descricao_padrao" value={form.descricao_padrao} onChange={handleChange} required />
            <Select label="Tipo" name="tipo" options={TIPO_ITEM_OPTIONS} value={form.tipo} onChange={handleChange} />
            <div className={form.tipo === 'SAIDA' ? 'opacity-50 cursor-not-allowed' : ''}>
              <Select
                label="Natureza"
                name="natureza"
                options={NATUREZA_OPTIONS}
                value={form.natureza}
                onChange={handleChange}
                disabled={form.tipo === 'SAIDA'}
              />
              {form.tipo === 'SAIDA' && (
                <p className="text-xs text-gray-400 mt-1">Aplicável apenas para Tipo = Entrada</p>
              )}
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={closeModal}>Cancelar</Button>
              <Button type="submit" loading={saving}>{editingId ? 'Salvar' : 'Cadastrar'}</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

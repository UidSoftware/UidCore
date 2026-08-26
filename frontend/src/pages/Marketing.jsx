import { useState, useEffect, useCallback } from 'react'
import { Plus, TrendingUp, Pencil, Trash2, UserCheck, Megaphone, Users } from 'lucide-react'
import api from '../api/client.js'
import { extractErrorMessage, stripEmptyStrings } from '../utils/errors.js'
import Card from '../components/ui/Card.jsx'
import Button from '../components/ui/Button.jsx'
import Input from '../components/ui/Input.jsx'
import Select from '../components/ui/Select.jsx'
import Modal from '../components/ui/Modal.jsx'
import Pagination from '../components/ui/Pagination.jsx'
import Loading from '../components/ui/Loading.jsx'

const PAGE_SIZE = 12

const TABS = [
  { key: 'campanhas', label: 'Campanhas' },
  { key: 'leads', label: 'Leads' },
]

const BRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

// --- Campanhas ---

const CANAL_OPTIONS = [
  { value: 'ads', label: 'Ads' },
  { value: 'redes_sociais', label: 'Redes Sociais' },
  { value: 'email', label: 'E-mail' },
  { value: 'organico', label: 'Orgânico' },
  { value: 'outro', label: 'Outro' },
]
const CANAL_FILTRO_OPTIONS = [{ value: '', label: 'Todos' }, ...CANAL_OPTIONS]

const STATUS_CAMPANHA_OPTIONS = [
  { value: 'planejada', label: 'Planejada' },
  { value: 'ativa', label: 'Ativa' },
  { value: 'encerrada', label: 'Encerrada' },
]
const STATUS_CAMPANHA_FILTRO_OPTIONS = [{ value: '', label: 'Todos' }, ...STATUS_CAMPANHA_OPTIONS]

const STATUS_BADGES_CAMPANHA = {
  planejada: 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400',
  ativa: 'bg-green-100 text-green-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  encerrada: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
}

const EMPTY_CAMPANHA = {
  nome: '', canal: 'ads', data_inicio: '', data_fim: '', orcamento: '', status: 'planejada',
}

const CANAL_LABEL = Object.fromEntries(CANAL_OPTIONS.map((c) => [c.value, c.label]))

function formatData(d) {
  if (!d) return null
  const [ano, mes, dia] = d.split('-')
  return `${dia}/${mes}/${ano}`
}

function CampanhasTab({ showToast }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [statusFiltro, setStatusFiltro] = useState('')
  const [canalFiltro, setCanalFiltro] = useState('')

  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(EMPTY_CAMPANHA)
  const [erroData, setErroData] = useState('')

  const [roiOpen, setRoiOpen] = useState(false)
  const [roiLoading, setRoiLoading] = useState(false)
  const [roiData, setRoiData] = useState(null)
  const [roiCampanhaNome, setRoiCampanhaNome] = useState('')

  const temFiltro = statusFiltro !== '' || canalFiltro !== ''

  const fetchItems = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page, page_size: PAGE_SIZE }
      if (statusFiltro) params.status = statusFiltro
      if (canalFiltro) params.canal = canalFiltro
      const r = await api.get('/marketing/campanhas/', { params })
      setItems(r.data.results || [])
      const count = r.data.count ?? (r.data.results || []).length
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao carregar campanhas.'), 'error')
    } finally {
      setLoading(false)
    }
  }, [page, statusFiltro, canalFiltro])

  useEffect(() => { fetchItems() }, [fetchItems])

  const limparFiltros = () => { setStatusFiltro(''); setCanalFiltro(''); setPage(1) }

  const handleChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }))

  const openNew = () => { setForm(EMPTY_CAMPANHA); setEditingId(null); setErroData(''); setModalOpen(true) }
  const openEdit = (item) => {
    setForm({
      nome: item.nome || '',
      canal: item.canal || 'ads',
      data_inicio: item.data_inicio || '',
      data_fim: item.data_fim || '',
      orcamento: item.orcamento ?? '',
      status: item.status || 'planejada',
    })
    setEditingId(item.id)
    setErroData('')
    setModalOpen(true)
  }
  const closeModal = () => { setModalOpen(false); setEditingId(null); setErroData('') }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.data_fim && form.data_inicio && form.data_fim < form.data_inicio) {
      setErroData('Data de fim não pode ser anterior à data de início.')
      return
    }
    setErroData('')
    setSaving(true)
    try {
      const payload = stripEmptyStrings(form)
      if (editingId) {
        await api.patch(`/marketing/campanhas/${editingId}/`, payload)
        showToast('Campanha atualizada.')
      } else {
        await api.post('/marketing/campanhas/', payload)
        showToast('Campanha cadastrada.')
      }
      closeModal()
      fetchItems()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao salvar campanha.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (item) => {
    if (!window.confirm(`Excluir a campanha "${item.nome}"?`)) return
    try {
      await api.delete(`/marketing/campanhas/${item.id}/`)
      showToast('Campanha removida.')
      fetchItems()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao remover campanha.'), 'error')
    }
  }

  const abrirRoi = async (item) => {
    setRoiCampanhaNome(item.nome)
    setRoiOpen(true)
    setRoiLoading(true)
    setRoiData(null)
    try {
      const r = await api.get(`/marketing/campanhas/${item.id}/roi/`)
      setRoiData(r.data)
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao carregar ROI.'), 'error')
      setRoiOpen(false)
    } finally {
      setRoiLoading(false)
    }
  }
  const closeRoi = () => { setRoiOpen(false); setRoiData(null) }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-slate-200">Campanhas</h2>
        <Button onClick={openNew}>
          <Plus size={16} /> Nova Campanha
        </Button>
      </div>

      <div className="flex flex-row flex-wrap gap-3 items-end">
        <Select
          options={STATUS_CAMPANHA_FILTRO_OPTIONS}
          value={statusFiltro}
          onChange={(e) => { setStatusFiltro(e.target.value); setPage(1) }}
          className="w-40"
        />
        <Select
          options={CANAL_FILTRO_OPTIONS}
          value={canalFiltro}
          onChange={(e) => { setCanalFiltro(e.target.value); setPage(1) }}
          className="w-44"
        />
        {temFiltro && (
          <Button variant="secondary" size="sm" onClick={limparFiltros} className="text-xs text-gray-500 dark:text-slate-400">
            Limpar filtros
          </Button>
        )}
      </div>

      {loading ? (
        <Loading message="Carregando campanhas..." />
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400 dark:text-slate-500">
          <Megaphone size={32} className="text-gray-300 dark:text-navy-600" />
          <p className="text-sm">Nenhuma campanha encontrada.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((item) => (
              <Card
                key={item.id}
                footer={
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1">
                      <Button size="sm" variant="secondary" onClick={() => openEdit(item)} title="Editar">
                        <Pencil size={14} /> <span className="hidden md:inline">Editar</span>
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => handleDelete(item)} title="Excluir" className="text-red-600 dark:text-red-400">
                        <Trash2 size={14} /> <span className="hidden md:inline">Excluir</span>
                      </Button>
                    </div>
                    <Button size="sm" variant="secondary" onClick={() => abrirRoi(item)} className="text-violet-600 dark:text-violet-400">
                      <TrendingUp size={14} /> Ver ROI
                    </Button>
                  </div>
                }
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="font-semibold text-gray-900 dark:text-slate-100">{item.nome}</p>
                  <span className={`shrink-0 text-xs rounded-full px-2 py-0.5 font-semibold ${STATUS_BADGES_CAMPANHA[item.status] || STATUS_BADGES_CAMPANHA.planejada}`}>
                    {item.status_display || item.status}
                  </span>
                </div>
                <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">📣 {item.canal_display || CANAL_LABEL[item.canal] || item.canal}</p>
                <p className="text-xs text-gray-400 dark:text-slate-500">
                  {formatData(item.data_inicio) || '—'} — {formatData(item.data_fim) || 'sem previsão'}
                </p>
                <p className="text-lg font-bold text-gray-900 dark:text-slate-100 mt-2">Orçamento: {BRL(item.orcamento)}</p>
              </Card>
            ))}
          </div>
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}

      {modalOpen && (
        <Modal title={editingId ? 'Editar Campanha' : 'Nova Campanha'} onClose={closeModal}>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label="Nome" name="nome" value={form.nome} onChange={handleChange} required />
            <Select label="Canal" name="canal" options={CANAL_OPTIONS} value={form.canal} onChange={handleChange} required />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <Input label="Data de Início" name="data_inicio" type="date" value={form.data_inicio} onChange={handleChange} required />
              <Input label="Data de Fim" name="data_fim" type="date" value={form.data_fim} onChange={handleChange} placeholder="Opcional" />
            </div>
            {erroData && <p className="text-xs text-red-600 dark:text-red-400 -mt-2">{erroData}</p>}
            <Input label="Orçamento (R$)" name="orcamento" type="number" step="0.01" min="0" value={form.orcamento} onChange={handleChange} />
            <Select label="Status" name="status" options={STATUS_CAMPANHA_OPTIONS} value={form.status} onChange={handleChange} required />
            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={closeModal}>Cancelar</Button>
              <Button type="submit" loading={saving}>Salvar</Button>
            </div>
          </form>
        </Modal>
      )}

      {roiOpen && (
        <Modal title={`ROI — ${roiCampanhaNome}`} onClose={closeRoi}>
          {roiLoading || !roiData ? (
            <Loading message="Calculando ROI..." />
          ) : (
            <div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <div className="bg-gray-50 dark:bg-navy-900/50 rounded-lg p-3">
                  <p className="text-xs text-gray-400 dark:text-slate-500 uppercase tracking-wide">Leads Totais</p>
                  <p className="text-lg font-bold text-gray-900 dark:text-slate-100">{roiData.leads_total}</p>
                </div>
                <div className="bg-gray-50 dark:bg-navy-900/50 rounded-lg p-3">
                  <p className="text-xs text-gray-400 dark:text-slate-500 uppercase tracking-wide">Leads Convertidos</p>
                  <p className="text-lg font-bold text-gray-900 dark:text-slate-100">{roiData.leads_convertidos}</p>
                </div>
                <div className="bg-gray-50 dark:bg-navy-900/50 rounded-lg p-3">
                  <p className="text-xs text-gray-400 dark:text-slate-500 uppercase tracking-wide">Orçamento</p>
                  <p className="text-lg font-bold text-gray-900 dark:text-slate-100">{BRL(roiData.orcamento)}</p>
                </div>
                <div className="bg-gray-50 dark:bg-navy-900/50 rounded-lg p-3">
                  <p className="text-xs text-gray-400 dark:text-slate-500 uppercase tracking-wide">Receita Fechada</p>
                  <p className="text-lg font-bold text-gray-900 dark:text-slate-100">{BRL(roiData.receita_fechada)}</p>
                </div>
                <div className="bg-gray-50 dark:bg-navy-900/50 rounded-lg p-3">
                  <p className="text-xs text-gray-400 dark:text-slate-500 uppercase tracking-wide">CAC</p>
                  <p className="text-lg font-bold text-gray-900 dark:text-slate-100">
                    {roiData.cac === null || roiData.cac === undefined ? '—' : BRL(roiData.cac)}
                  </p>
                </div>
                <div className="bg-gray-50 dark:bg-navy-900/50 rounded-lg p-3">
                  <p className="text-xs text-gray-400 dark:text-slate-500 uppercase tracking-wide">ROI</p>
                  <p className={`text-lg font-bold ${
                    roiData.roi === null || roiData.roi === undefined
                      ? 'text-gray-900 dark:text-slate-100'
                      : Number(roiData.roi) < 0
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-green-600 dark:text-emerald-400'
                  }`}>
                    {roiData.roi === null || roiData.roi === undefined
                      ? '—'
                      : `${Number(roiData.roi) > 0 ? '+' : ''}${Number(roiData.roi).toFixed(1)}%`}
                  </p>
                </div>
              </div>

              <div className="mt-4">
                <div className="flex justify-between text-xs text-gray-400 dark:text-slate-500 mb-1">
                  <span>Taxa de conversão</span>
                  <span>{roiData.leads_total > 0 ? Math.round((roiData.leads_convertidos / roiData.leads_total) * 100) : 0}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-gray-100 dark:bg-navy-700 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-violet-500 transition-all"
                    style={{ width: `${roiData.leads_total > 0 ? (roiData.leads_convertidos / roiData.leads_total) * 100 : 0}%` }}
                  />
                </div>
              </div>

              <div className="flex justify-end pt-4">
                <Button variant="secondary" onClick={closeRoi}>Fechar</Button>
              </div>
            </div>
          )}
        </Modal>
      )}
    </div>
  )
}

// --- Leads ---

const STATUS_LEAD_OPTIONS = [
  { value: 'novo', label: 'Novo' },
  { value: 'qualificado', label: 'Qualificado' },
  { value: 'convertido', label: 'Convertido' },
  { value: 'descartado', label: 'Descartado' },
]
const STATUS_LEAD_FILTRO_OPTIONS = [{ value: '', label: 'Todos' }, ...STATUS_LEAD_OPTIONS]

const STATUS_BADGES_LEAD = {
  novo: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  qualificado: 'bg-yellow-100 text-yellow-700 dark:bg-amber-900/30 dark:text-amber-300',
  convertido: 'bg-green-100 text-green-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  descartado: 'bg-gray-100 text-gray-500 dark:bg-navy-700 dark:text-slate-500',
}

const EMPTY_LEAD = {
  nome: '', email: '', telefone: '', campanha: '', observacoes: '', status: 'novo',
}

function LeadsTab({ showToast }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [statusFiltro, setStatusFiltro] = useState('')
  const [campanhaFiltro, setCampanhaFiltro] = useState('')
  const [campanhas, setCampanhas] = useState([])

  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editingStatusOriginal, setEditingStatusOriginal] = useState(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(EMPTY_LEAD)
  const [convertendoId, setConvertendoId] = useState(null)

  const temFiltro = statusFiltro !== '' || campanhaFiltro !== ''

  useEffect(() => {
    api.get('/marketing/campanhas/', { params: { page_size: 200 } })
      .then((r) => setCampanhas(r.data.results || []))
      .catch(() => setCampanhas([]))
  }, [])

  const campanhaOptions = [
    { value: '', label: 'Sem campanha' },
    ...campanhas.map((c) => ({ value: String(c.id), label: c.nome })),
  ]
  const campanhaFiltroOptions = [
    { value: '', label: 'Todos' },
    { value: 'sem_campanha', label: 'Sem campanha' },
    ...campanhas.map((c) => ({ value: String(c.id), label: c.nome })),
  ]

  const fetchItems = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page, page_size: PAGE_SIZE }
      if (statusFiltro) params.status = statusFiltro
      if (campanhaFiltro && campanhaFiltro !== 'sem_campanha') params.campanha = campanhaFiltro
      const r = await api.get('/marketing/leads/', { params })
      let results = r.data.results || []
      let count = r.data.count ?? results.length
      if (campanhaFiltro === 'sem_campanha') {
        results = results.filter((l) => !l.campanha)
        count = results.length
      }
      setItems(results)
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao carregar leads.'), 'error')
    } finally {
      setLoading(false)
    }
  }, [page, statusFiltro, campanhaFiltro])

  useEffect(() => { fetchItems() }, [fetchItems])

  const limparFiltros = () => { setStatusFiltro(''); setCampanhaFiltro(''); setPage(1) }

  const handleChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }))

  const openNew = () => { setForm(EMPTY_LEAD); setEditingId(null); setEditingStatusOriginal(null); setModalOpen(true) }
  const openEdit = (item) => {
    setForm({
      nome: item.nome || '',
      email: item.email || '',
      telefone: item.telefone || '',
      campanha: item.campanha ? String(item.campanha) : '',
      observacoes: item.observacoes || '',
      status: item.status || 'novo',
    })
    setEditingId(item.id)
    setEditingStatusOriginal(item.status)
    setModalOpen(true)
  }
  const closeModal = () => { setModalOpen(false); setEditingId(null); setEditingStatusOriginal(null) }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = stripEmptyStrings(form)
      payload.campanha = form.campanha || null
      if (editingId) {
        await api.patch(`/marketing/leads/${editingId}/`, payload)
        showToast('Lead atualizado.')
      } else {
        await api.post('/marketing/leads/', payload)
        showToast('Lead cadastrado.')
      }
      closeModal()
      fetchItems()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao salvar lead.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (item) => {
    if (!window.confirm(`Excluir o lead "${item.nome}"?`)) return
    try {
      await api.delete(`/marketing/leads/${item.id}/`)
      showToast('Lead removido.')
      fetchItems()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao remover lead.'), 'error')
    }
  }

  const handleConverter = async (item) => {
    setConvertendoId(item.id)
    try {
      await api.post(`/marketing/leads/${item.id}/converter/`)
      showToast('Lead convertido em cliente com sucesso.')
      fetchItems()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao converter lead.'), 'error')
    } finally {
      setConvertendoId(null)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-slate-200">Leads</h2>
        <Button onClick={openNew}>
          <Plus size={16} /> Novo Lead
        </Button>
      </div>

      <div className="flex flex-row flex-wrap gap-3 items-end">
        <Select
          options={STATUS_LEAD_FILTRO_OPTIONS}
          value={statusFiltro}
          onChange={(e) => { setStatusFiltro(e.target.value); setPage(1) }}
          className="w-40"
        />
        <Select
          options={campanhaFiltroOptions}
          value={campanhaFiltro}
          onChange={(e) => { setCampanhaFiltro(e.target.value); setPage(1) }}
          className="w-52"
        />
        {temFiltro && (
          <Button variant="secondary" size="sm" onClick={limparFiltros} className="text-xs text-gray-500 dark:text-slate-400">
            Limpar filtros
          </Button>
        )}
      </div>

      {loading ? (
        <Loading message="Carregando leads..." />
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400 dark:text-slate-500">
          <Users size={32} className="text-gray-300 dark:text-navy-600" />
          <p className="text-sm">Nenhum lead encontrado.</p>
        </div>
      ) : (
        <>
          <Card>
            <div className="overflow-x-auto -mx-6 -my-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200 dark:bg-navy-900 dark:border-navy-600">
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Nome</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">E-mail</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Telefone</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Campanha</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Status</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-navy-700">
                  {items.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-navy-700/60">
                      <td className="px-4 py-3 font-medium text-gray-900 dark:text-slate-100">{item.nome}</td>
                      <td className="px-4 py-3 text-gray-500 dark:text-slate-400">{item.email || '—'}</td>
                      <td className="px-4 py-3 text-gray-500 dark:text-slate-400">{item.telefone || '—'}</td>
                      <td className="px-4 py-3">
                        {item.campanha_nome ? (
                          <span className="text-gray-600 dark:text-slate-400">{item.campanha_nome}</span>
                        ) : (
                          <span className="text-gray-400 dark:text-slate-500 italic">Sem campanha</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs rounded-full px-2 py-0.5 font-semibold ${STATUS_BADGES_LEAD[item.status] || STATUS_BADGES_LEAD.novo}`}>
                          {item.status_display || item.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end items-center gap-2">
                          {item.status !== 'convertido' && (
                            <Button
                              size="sm"
                              variant="secondary"
                              loading={convertendoId === item.id}
                              onClick={() => handleConverter(item)}
                              className="text-violet-600 border-violet-500 dark:text-violet-400"
                            >
                              <UserCheck size={14} /> Converter
                            </Button>
                          )}
                          <Button size="sm" variant="secondary" onClick={() => openEdit(item)} title="Editar">
                            <Pencil size={14} />
                          </Button>
                          <Button size="sm" variant="secondary" onClick={() => handleDelete(item)} title="Excluir" className="text-red-600 dark:text-red-400">
                            <Trash2 size={14} />
                          </Button>
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
        <Modal title={editingId ? 'Editar Lead' : 'Novo Lead'} onClose={closeModal}>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label="Nome" name="nome" value={form.nome} onChange={handleChange} required />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <Input label="E-mail" name="email" type="email" value={form.email} onChange={handleChange} />
              <Input label="Telefone" name="telefone" value={form.telefone} onChange={handleChange} placeholder="(11) 99999-0000" />
            </div>
            <Select label="Campanha" name="campanha" options={campanhaOptions} value={form.campanha} onChange={handleChange} />
            <div>
              <Select
                label="Status"
                name="status"
                options={STATUS_LEAD_OPTIONS}
                value={form.status}
                onChange={handleChange}
                disabled={editingStatusOriginal === 'convertido'}
              />
              {editingStatusOriginal === 'convertido' && (
                <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
                  Conversão é irreversível — use a ação Converter em Cliente na listagem para leads não convertidos.
                </p>
              )}
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Observações</label>
              <textarea
                name="observacoes"
                value={form.observacoes}
                onChange={handleChange}
                rows={2}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={closeModal}>Cancelar</Button>
              <Button type="submit" loading={saving}>Salvar</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

// --- Componente principal ---
export default function Marketing() {
  const [tab, setTab] = useState('campanhas')
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
        <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100">Marketing</h1>
      </div>

      <div className="flex gap-1 overflow-x-auto pb-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium rounded-lg whitespace-nowrap transition-colors ${
              tab === t.key
                ? 'bg-primary-600 text-white dark:bg-violet-600'
                : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200 dark:bg-navy-800 dark:text-slate-400 dark:hover:bg-navy-700 dark:border-navy-600'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'campanhas' && <CampanhasTab showToast={showToast} />}
      {tab === 'leads' && <LeadsTab showToast={showToast} />}
    </div>
  )
}

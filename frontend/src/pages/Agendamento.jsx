import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Clock, CalendarDays, Users, Plus, Pencil,
  CheckCircle, X, RefreshCw, CalendarCheck,
  Shield, Globe, AlertTriangle, User,
} from 'lucide-react'
import api from '../api/client.js'
import { extractErrorMessage } from '../utils/errors.js'
import ResourceCrud from '../components/ui/ResourceCrud.jsx'
import CalendarioTab from './agendamento/CalendarioTab.jsx'
import Modal from '../components/ui/Modal.jsx'
import Input from '../components/ui/Input.jsx'
import Select from '../components/ui/Select.jsx'
import Button from '../components/ui/Button.jsx'

const TABS = [
  { key: 'compromissos', label: 'Compromissos' },
  { key: 'agendas', label: 'Agendas' },
  { key: 'calendario', label: 'Calendário' },
  { key: 'horarios', label: 'Horários' },
  { key: 'pendentes', label: 'Pendentes' },
]

export const STATUS_COMPROMISSO = [
  { value: 'AGENDADO', label: 'Agendado' },
  { value: 'CONFIRMADO', label: 'Confirmado' },
  { value: 'CANCELADO', label: 'Cancelado' },
  { value: 'CONCLUIDO', label: 'Concluído' },
]

const DIAS_SEMANA_OPTIONS = [
  { value: '', label: 'Selecione...' },
  { value: '0', label: 'Segunda' },
  { value: '1', label: 'Terça' },
  { value: '2', label: 'Quarta' },
  { value: '3', label: 'Quinta' },
  { value: '4', label: 'Sexta' },
  { value: '5', label: 'Sábado' },
  { value: '6', label: 'Domingo' },
]

const DIAS_SEMANA_LABELS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']

// ---------------------------------------------------------------------------
// Aba Horários
// ---------------------------------------------------------------------------

function HorariosTab() {
  const [agendas, setAgendas] = useState([])
  const [agendaSelecionada, setAgendaSelecionada] = useState('')
  const [horarios, setHorarios] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)
  const [errors, setErrors] = useState({})

  const emptyForm = {
    dia_semana: '',
    hora_inicio: '',
    duracao_minutos: '',
    vagas: '',
    servico: '',
    publico: true,
    ativo: true,
  }
  const [form, setForm] = useState(emptyForm)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), type === 'error' ? 7000 : 3500)
  }

  useEffect(() => {
    api.get('/agendamento/agendas/', { params: { page_size: 200 } })
      .then((r) => setAgendas(r.data.results))
      .catch(() => setAgendas([]))
  }, [])

  const fetchHorarios = useCallback(async () => {
    if (!agendaSelecionada) return
    setLoading(true)
    try {
      const r = await api.get('/agendamento/horarios-disponiveis/', {
        params: { agenda: agendaSelecionada, page_size: 200 },
      })
      setHorarios(r.data.results)
    } catch {
      showToast('Erro ao carregar horários.', 'error')
    } finally {
      setLoading(false)
    }
  }, [agendaSelecionada])

  useEffect(() => {
    fetchHorarios()
  }, [fetchHorarios])

  const openNew = () => {
    setEditingItem(null)
    setForm({ ...emptyForm, agenda: agendaSelecionada })
    setErrors({})
    setModalOpen(true)
  }

  const openEdit = (item) => {
    setEditingItem(item)
    setForm({
      dia_semana: String(item.dia_semana),
      hora_inicio: item.hora_inicio,
      duracao_minutos: item.duracao_minutos,
      vagas: item.vagas,
      servico: item.servico || '',
      publico: item.publico,
      ativo: item.ativo,
    })
    setErrors({})
    setModalOpen(true)
  }

  const closeModal = () => {
    setModalOpen(false)
    setEditingItem(null)
    setForm(emptyForm)
    setErrors({})
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }))
  }

  const validate = () => {
    const errs = {}
    if (form.dia_semana === '') errs.dia_semana = 'Obrigatório'
    if (!form.hora_inicio) errs.hora_inicio = 'Obrigatório'
    if (!form.duracao_minutos || Number(form.duracao_minutos) < 5) errs.duracao_minutos = 'Mínimo 5 min'
    if (!form.vagas || Number(form.vagas) < 1) errs.vagas = 'Mínimo 1 vaga'
    return errs
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length > 0) { setErrors(errs); return }

    setSaving(true)
    try {
      const payload = {
        agenda: agendaSelecionada,
        dia_semana: Number(form.dia_semana),
        hora_inicio: form.hora_inicio,
        duracao_minutos: Number(form.duracao_minutos),
        vagas: Number(form.vagas),
        servico: form.servico,
        publico: form.publico,
        ativo: form.ativo,
      }
      if (editingItem) {
        await api.patch(`/agendamento/horarios-disponiveis/${editingItem.id}/`, payload)
        showToast('Horário atualizado.')
      } else {
        await api.post('/agendamento/horarios-disponiveis/', payload)
        showToast('Horário criado.')
      }
      closeModal()
      fetchHorarios()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao salvar.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const toggleAtivo = async (item) => {
    try {
      await api.patch(`/agendamento/horarios-disponiveis/${item.id}/`, { ativo: !item.ativo })
      showToast(item.ativo ? 'Horário desativado.' : 'Horário ativado.')
      fetchHorarios()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao atualizar.'), 'error')
    }
  }

  const agendasOptions = [
    { value: '', label: 'Selecione uma agenda...' },
    ...agendas.map((a) => ({ value: String(a.id), label: a.nome })),
  ]

  return (
    <div className="space-y-4">
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white ${
            toast.type === 'error' ? 'bg-red-600' : 'bg-accent-600 dark:bg-violet-600'
          }`}
        >
          {toast.msg}
        </div>
      )}

      <div className="flex items-center justify-between gap-4">
        <div className="w-64">
          <Select
            label="Agenda"
            options={agendasOptions}
            value={agendaSelecionada}
            onChange={(e) => setAgendaSelecionada(e.target.value)}
          />
        </div>
        {agendaSelecionada && (
          <Button onClick={openNew} size="md">
            <Plus size={14} />
            Novo Horário
          </Button>
        )}
      </div>

      {!agendaSelecionada ? (
        <div className="flex flex-col items-center justify-center py-12 gap-3 text-slate-500">
          <CalendarDays size={32} />
          <p className="text-sm">Selecione uma agenda para ver os horários.</p>
        </div>
      ) : loading ? (
        <div className="flex justify-center py-12 text-slate-500 text-sm">Carregando...</div>
      ) : horarios.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-3 text-slate-500">
          <Clock size={32} />
          <p className="text-sm">Nenhum horário cadastrado para esta agenda.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-navy-600">
          <table className="w-full">
            <thead className="bg-navy-900">
              <tr>
                {['Dia', 'Hora', 'Duração', 'Serviço', 'Vagas', 'Público', 'Ativo', 'Ações'].map((col) => (
                  <th
                    key={col}
                    className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide text-left"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {horarios.map((h) => (
                <tr
                  key={h.id}
                  className="border-b border-navy-700 hover:bg-navy-700/40 transition-colors"
                >
                  <td className="px-4 py-3 text-sm text-slate-200 font-medium">
                    {h.dia_semana_label || DIAS_SEMANA_LABELS[h.dia_semana] || '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-200">
                    {h.hora_inicio ? h.hora_inicio.slice(0, 5) : '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-400">{h.duracao_minutos} min</td>
                  <td className="px-4 py-3 text-sm text-slate-200">{h.servico || '—'}</td>
                  <td className="px-4 py-3 text-sm text-slate-200 font-medium">{h.vagas}</td>
                  <td className="px-4 py-3">
                    {h.publico ? (
                      <span className="bg-violet-400/15 text-violet-400 border border-violet-400/30 rounded-full px-2 py-0.5 text-xs font-medium">
                        Público
                      </span>
                    ) : (
                      <span className="bg-navy-600 text-slate-500 rounded-full px-2 py-0.5 text-xs font-medium">
                        Privado
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleAtivo(h)}
                      title={h.ativo ? 'Desativar' : 'Ativar'}
                      className={`relative inline-flex h-5 w-9 cursor-pointer items-center rounded-full transition-colors ${
                        h.ativo ? 'bg-emerald-500' : 'bg-navy-600'
                      }`}
                    >
                      <span
                        className={`absolute h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
                          h.ativo ? 'translate-x-4' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => openEdit(h)}
                      title="Editar"
                      className="text-slate-500 hover:text-violet-400 transition-colors cursor-pointer"
                    >
                      <Pencil size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modalOpen && (
        <Modal
          title={editingItem ? 'Editar Horário' : 'Novo Horário'}
          onClose={closeModal}
          maxW="max-w-md"
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Select
                label="Dia da Semana *"
                options={DIAS_SEMANA_OPTIONS}
                name="dia_semana"
                value={form.dia_semana}
                onChange={handleChange}
                error={errors.dia_semana}
              />
              <Input
                label="Hora de Início *"
                type="time"
                name="hora_inicio"
                value={form.hora_inicio}
                onChange={handleChange}
                step="300"
                error={errors.hora_inicio}
              />
              <Input
                label="Duração (min) *"
                type="number"
                name="duracao_minutos"
                value={form.duracao_minutos}
                onChange={handleChange}
                min="5"
                step="5"
                placeholder="30"
                error={errors.duracao_minutos}
              />
              <Input
                label="Vagas *"
                type="number"
                name="vagas"
                value={form.vagas}
                onChange={handleChange}
                min="1"
                placeholder="1"
                error={errors.vagas}
              />
            </div>
            <Input
              label="Serviço (rótulo livre)"
              type="text"
              name="servico"
              value={form.servico}
              onChange={handleChange}
              placeholder="ex: Consulta 30min"
            />
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <input
                  id="publico-check"
                  type="checkbox"
                  name="publico"
                  checked={!!form.publico}
                  onChange={handleChange}
                  className="w-4 h-4 rounded accent-violet-600"
                />
                <label htmlFor="publico-check" className="text-sm text-slate-300">
                  Horário visível no agendamento público
                </label>
              </div>
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <input
                    id="ativo-check"
                    type="checkbox"
                    name="ativo"
                    checked={!!form.ativo}
                    onChange={handleChange}
                    className="w-4 h-4 rounded accent-violet-600"
                  />
                  <label htmlFor="ativo-check" className="text-sm text-slate-300">
                    Aceitar novos agendamentos
                  </label>
                </div>
                <p className="text-xs text-slate-500 ml-6">
                  Desativar impede novos agendamentos, mas não cancela os já existentes.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6 pt-4 border-t border-navy-600">
              <Button type="button" variant="secondary" size="md" onClick={closeModal}>
                Cancelar
              </Button>
              <Button type="submit" variant="primary" size="md" loading={saving}>
                Salvar Horário
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Aba Pendentes
// ---------------------------------------------------------------------------

function PendentesTab({ onCountChange }) {
  const [pendentes, setPendentes] = useState([])
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState(null)
  const [confirmandoId, setConfirmandoId] = useState(null)
  const [recusandoId, setRecusandoId] = useState(null)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), type === 'error' ? 7000 : 3500)
  }

  const fetchPendentes = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.get('/agendamento/compromissos/', {
        params: { origem: 'PUBLICO', status: 'AGENDADO', page_size: 200 },
      })
      const results = r.data.results
      setPendentes(results)
      onCountChange?.(results.length)
    } catch {
      showToast('Erro ao carregar pendentes.', 'error')
    } finally {
      setLoading(false)
    }
  }, [onCountChange])

  useEffect(() => {
    fetchPendentes()
  }, [fetchPendentes])

  const confirmar = async (id) => {
    setConfirmandoId(id)
    try {
      await api.patch(`/agendamento/compromissos/${id}/`, { status: 'CONFIRMADO' })
      showToast('Agendamento confirmado.')
      fetchPendentes()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao confirmar.'), 'error')
    } finally {
      setConfirmandoId(null)
    }
  }

  const recusar = async (id) => {
    try {
      await api.patch(`/agendamento/compromissos/${id}/`, { status: 'CANCELADO' })
      showToast('Agendamento recusado.')
      setRecusandoId(null)
      fetchPendentes()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao recusar.'), 'error')
    }
  }

  const formatarDataHora = (dataStr) => {
    if (!dataStr) return '—'
    const dias = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
    const d = new Date(dataStr + 'T00:00:00')
    const dia = dias[d.getDay()]
    return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')} — ${dia}`
  }

  const tempoRelativo = (isoStr) => {
    if (!isoStr) return '—'
    const diff = Date.now() - new Date(isoStr).getTime()
    const min = Math.floor(diff / 60000)
    if (min < 60) return `há ${min}min`
    const h = Math.floor(min / 60)
    if (h < 24) return `há ${h}h`
    return `há ${Math.floor(h / 24)}d`
  }

  return (
    <div className="space-y-4">
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white ${
            toast.type === 'error' ? 'bg-red-600' : 'bg-accent-600 dark:bg-violet-600'
          }`}
        >
          {toast.msg}
        </div>
      )}

      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-slate-100">Pendentes de Confirmação</h2>
            {pendentes.length > 0 && (
              <span className="bg-amber-400/20 text-amber-400 border border-amber-400/30 rounded-full px-2 py-0.5 text-xs font-bold">
                {pendentes.length}
              </span>
            )}
          </div>
          <p className="text-sm text-slate-400 mt-0.5">
            Compromissos recebidos pelo agendamento público aguardando confirmação.
          </p>
        </div>
        <button
          onClick={fetchPendentes}
          title="Atualizar"
          className="text-slate-500 hover:text-slate-300 cursor-pointer mt-1"
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12 text-slate-500 text-sm">Carregando...</div>
      ) : pendentes.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-3 text-slate-500">
          <CalendarCheck size={32} />
          <p className="text-sm">Nenhum agendamento pendente.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-navy-600">
          <table className="w-full">
            <thead className="bg-navy-900">
              <tr>
                {['Contato', 'Telefone', 'Data', 'Serviço', 'Recebido em', 'Ações'].map((col) => (
                  <th
                    key={col}
                    className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide text-left"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pendentes.map((p) => (
                <tr
                  key={p.id}
                  className="border-b border-navy-700 hover:bg-navy-700/40 transition-colors"
                >
                  <td className="px-4 py-3">
                    <p className="text-sm text-slate-200 font-medium">{p.nome_contato || '—'}</p>
                    {p.email_contato && (
                      <p className="text-xs text-slate-500">{p.email_contato}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-300">{p.telefone_contato || '—'}</td>
                  <td className="px-4 py-3 text-sm text-slate-300">{formatarDataHora(p.data_horario)}</td>
                  <td className="px-4 py-3 text-sm text-slate-400">{p.horario_servico || '—'}</td>
                  <td className="px-4 py-3 text-xs text-slate-500">{tempoRelativo(p.created_at)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        loading={confirmandoId === p.id}
                        onClick={() => confirmar(p.id)}
                        className="dark:border-emerald-500/50 dark:text-emerald-400 dark:hover:bg-emerald-500/10"
                      >
                        <CheckCircle size={14} />
                        Confirmar
                      </Button>
                      <div className="relative">
                        <button
                          onClick={() => setRecusandoId(recusandoId === p.id ? null : p.id)}
                          title="Recusar agendamento"
                          className="text-slate-500 hover:text-red-400 transition-colors"
                        >
                          <X size={14} />
                        </button>
                        {recusandoId === p.id && (
                          <div className="absolute right-0 top-6 z-10 bg-navy-800 border border-navy-600 rounded-lg p-3 shadow-xl text-sm whitespace-nowrap">
                            <p className="text-slate-300 mb-2">Recusar este agendamento?</p>
                            <div className="flex gap-2">
                              <button
                                onClick={() => recusar(p.id)}
                                className="text-xs bg-red-600 text-white px-2 py-1 rounded-lg hover:bg-red-700"
                              >
                                Sim, recusar
                              </button>
                              <button
                                onClick={() => setRecusandoId(null)}
                                className="text-xs bg-navy-700 text-slate-300 px-2 py-1 rounded-lg hover:bg-navy-600"
                              >
                                Não
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Aba Compromissos (com formulário ampliado)
// ---------------------------------------------------------------------------

function CompromissosTab() {
  const [agendas, setAgendas] = useState([])
  const [horariosPorAgenda, setHorariosPorAgenda] = useState({})
  const [toast, setToast] = useState(null)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), type === 'error' ? 7000 : 3500)
  }

  useEffect(() => {
    api.get('/agendamento/agendas/', { params: { page_size: 200 } })
      .then((r) => setAgendas(r.data.results))
      .catch(() => {})
  }, [])

  const carregarHorariosDaAgenda = useCallback(async (agendaId) => {
    if (!agendaId || horariosPorAgenda[agendaId]) return
    try {
      const r = await api.get('/agendamento/horarios-disponiveis/', {
        params: { agenda: agendaId, ativo: true, page_size: 200 },
      })
      setHorariosPorAgenda((prev) => ({ ...prev, [agendaId]: r.data.results }))
    } catch {
      setHorariosPorAgenda((prev) => ({ ...prev, [agendaId]: [] }))
    }
  }, [horariosPorAgenda])

  // Campos do formulário ampliado (RF-15)
  const camposExtras = [
    // separador
    { name: '_sep1', type: 'divider' },
    // Horário disponível (condicional por agenda)
    { name: 'horario', label: 'Horário Disponível', type: 'select', options: [], _dynamic: true },
    // Data do horário (condicional por horário)
    { name: 'data_horario', label: 'Data do Horário', type: 'date', _condicional_horario: true },
    // separador
    { name: '_sep2', type: 'divider' },
    // Dados de contato (condicionais quando sem cliente)
    { name: 'nome_contato', label: 'Nome do contato', type: 'text', _condicional_contato: true },
    { name: 'telefone_contato', label: 'Telefone do contato', type: 'tel', placeholder: '(00) 00000-0000', _condicional_contato: true },
    { name: 'email_contato', label: 'Email (opcional)', type: 'email', _condicional_contato: true },
    // separador
    { name: '_sep3', type: 'divider' },
  ]

  // Usa ResourceCrud com customização de campos via onBeforeSubmit e
  // renderização de campos extras fora do grid padrão através da extensão
  // da lista de fields. Como ResourceCrud não suporta campos dinâmicos
  // condicionais complexos, usamos um componente wrapper customizado aqui.
  return (
    <div>
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white ${
            toast.type === 'error' ? 'bg-red-600' : 'bg-accent-600 dark:bg-violet-600'
          }`}
        >
          {toast.msg}
        </div>
      )}
      <CompromissosResourceCrud
        agendas={agendas}
        horariosPorAgenda={horariosPorAgenda}
        onCarregarHorarios={carregarHorariosDaAgenda}
        showToast={showToast}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// ResourceCrud Customizado para Compromissos (com campos ampliados RF-15)
// ---------------------------------------------------------------------------

function CompromissosResourceCrud({ agendas, horariosPorAgenda, onCarregarHorarios, showToast }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [clientesOptions, setClientesOptions] = useState([])
  const [conflito, setConflito] = useState(null)

  const PAGE_SIZE = 10

  const emptyForm = {
    titulo: '', agenda: '', cliente: '', horario: '', data_horario: '',
    nome_contato: '', telefone_contato: '', email_contato: '',
    inicio: '', fim: '', local: '', status: 'AGENDADO', descricao: '', observacoes: '',
  }
  const [form, setForm] = useState(emptyForm)

  const fetchItems = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.get('/agendamento/compromissos/', { params: { page, page_size: PAGE_SIZE } })
      setItems(r.data.results)
      setTotalPages(Math.max(1, Math.ceil(r.data.count / PAGE_SIZE)))
    } catch {
      showToast?.('Erro ao carregar compromissos.', 'error')
    } finally {
      setLoading(false)
    }
  }, [page, showToast])

  useEffect(() => { fetchItems() }, [fetchItems])

  useEffect(() => {
    api.get('/clientes/', { params: { page_size: 500 } })
      .then((r) => setClientesOptions(r.data.results))
      .catch(() => {})
  }, [])

  const openNew = () => {
    setEditingId(null)
    setForm(emptyForm)
    setConflito(null)
    setModalOpen(true)
  }

  const openEdit = (item) => {
    setEditingId(item.id)
    setConflito(null)
    const next = { ...emptyForm }
    for (const k of Object.keys(emptyForm)) {
      const v = item[k]
      if (v === null || v === undefined) { next[k] = ''; continue }
      if (k === 'inicio' || k === 'fim') { next[k] = v ? v.slice(0, 16) : ''; continue }
      next[k] = String(v)
    }
    setForm(next)
    if (item.agenda) onCarregarHorarios(item.agenda)
    setModalOpen(true)
  }

  const closeModal = () => {
    setModalOpen(false)
    setEditingId(null)
    setForm(emptyForm)
    setConflito(null)
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => {
      const next = { ...prev, [name]: value }
      // Ao mudar agenda, limpar horário
      if (name === 'agenda') {
        next.horario = ''
        next.data_horario = ''
        if (value) onCarregarHorarios(value)
      }
      // Ao mudar horário, limpar data_horario
      if (name === 'horario') {
        next.data_horario = ''
      }
      return next
    })
  }

  const handleDelete = async (item) => {
    if (!window.confirm(`Excluir "${item.titulo}"?`)) return
    try {
      await api.delete(`/agendamento/compromissos/${item.id}/`)
      showToast?.('Compromisso removido.')
      fetchItems()
    } catch (error) {
      showToast?.(extractErrorMessage(error, 'Erro ao remover.'), 'error')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setConflito(null)
    try {
      const payload = {}
      for (const [k, v] of Object.entries(form)) {
        if (v === '') continue
        payload[k] = v
      }
      let response
      if (editingId) {
        response = await api.patch(`/agendamento/compromissos/${editingId}/`, payload)
        showToast?.('Compromisso atualizado.')
      } else {
        response = await api.post('/agendamento/compromissos/', payload)
        showToast?.('Compromisso criado.')
      }
      if (response.data.aviso) {
        setConflito(response.data.aviso)
        // Manter modal aberto por 6s para mostrar o aviso, depois fechar
        setTimeout(() => { closeModal(); fetchItems() }, 6000)
      } else {
        closeModal()
        fetchItems()
      }
    } catch (error) {
      showToast?.(extractErrorMessage(error, 'Erro ao salvar.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const horariosDaAgenda = form.agenda ? (horariosPorAgenda[form.agenda] || []) : []
  const horarioOpts = [
    { value: '', label: form.agenda ? 'Nenhum (agendamento avulso)' : 'Selecione uma agenda primeiro' },
    ...horariosDaAgenda.map((h) => ({
      value: String(h.id),
      label: `${DIAS_SEMANA_LABELS[h.dia_semana]} ${h.hora_inicio?.slice(0, 5)} — ${h.servico || 'Sem rótulo'}`,
    })),
  ]

  const agendasOpts = [
    { value: '', label: 'Selecione...' },
    ...agendas.map((a) => ({ value: String(a.id), label: a.nome })),
  ]

  const clientesOpts = [
    { value: '', label: 'Selecione (opcional)...' },
    ...clientesOptions.map((c) => ({ value: String(c.id), label: c.nome_razao_social })),
  ]

  const horarioSelecionado = form.horario
    ? horariosDaAgenda.find((h) => String(h.id) === form.horario)
    : null
  const diaLabel = horarioSelecionado ? DIAS_SEMANA_LABELS[horarioSelecionado.dia_semana] : ''

  // Edição: obter origem do item atual
  const itemAtual = items.find((i) => i.id === editingId)
  const origemAtual = itemAtual?.origem || null

  const renderStatus = (s) => {
    const map = { 'Agendado': 'bg-violet-900/30 text-violet-300', 'Confirmado': 'bg-emerald-900/30 text-emerald-300', 'Cancelado': 'bg-red-900/20 text-red-400', 'Concluído': 'bg-navy-700 text-slate-400' }
    return <span className={`text-xs rounded-full px-2 py-0.5 font-medium ${map[s] || 'bg-navy-700 text-slate-400'}`}>{s}</span>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100">Compromissos</h2>
        <Button onClick={openNew}>+ Novo Compromisso</Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12 text-gray-400 dark:text-slate-500 text-sm">Carregando...</div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400 dark:text-slate-500">
          <span className="text-4xl">📅</span>
          <p className="text-sm">Nenhum compromisso encontrado.</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200 dark:bg-navy-900 dark:border-navy-600">
                  {['Título', 'Agenda', 'Cliente', 'Início', 'Status', 'Vagas'].map((col) => (
                    <th key={col} className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap dark:text-slate-400">{col}</th>
                  ))}
                  <th className="text-right px-6 py-3 font-semibold text-gray-600 whitespace-nowrap dark:text-slate-400">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-navy-700">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-navy-700/60 transition-colors">
                    <td className="px-4 py-3 text-gray-900 dark:text-slate-100 font-medium whitespace-nowrap">{item.titulo}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400 whitespace-nowrap">{item.agenda_nome || '—'}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400 whitespace-nowrap">
                      {item.cliente_nome || item.nome_contato || '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-400 whitespace-nowrap">
                      {item.inicio ? new Date(item.inicio).toLocaleString('pt-BR') : '—'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">{renderStatus(item.status_label)}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {item.horario && item.vagas_restantes !== null && item.vagas_restantes !== undefined ? (
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
                            item.vagas_restantes > 0
                              ? 'bg-emerald-400/15 text-emerald-400'
                              : 'bg-red-400/15 text-red-400'
                          }`}
                          title={item.vagas_restantes > 0 ? `${item.vagas_restantes} vagas disponíveis` : 'Horário lotado'}
                        >
                          <Users size={10} />
                          {item.horario
                            ? `${(horariosPorAgenda[item.agenda]?.find(h => h.id === item.horario)?.vagas || item.vagas_restantes) - item.vagas_restantes}/${horariosPorAgenda[item.agenda]?.find(h => h.id === item.horario)?.vagas || '?'}`
                            : `${item.vagas_restantes}`
                          }
                        </span>
                      ) : (
                        <span className="text-slate-500 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-6 py-3 text-right whitespace-nowrap">
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
          {totalPages > 1 && (
            <div className="flex justify-center gap-2 p-3 border-t border-gray-100 dark:border-navy-700">
              <Button size="sm" variant="secondary" disabled={page === 1} onClick={() => setPage(p => p - 1)}>‹</Button>
              <span className="text-sm text-slate-400 py-1">{page}/{totalPages}</span>
              <Button size="sm" variant="secondary" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>›</Button>
            </div>
          )}
        </div>
      )}

      {modalOpen && (
        <Modal
          title={editingId ? 'Editar Compromisso' : '+ Novo Compromisso'}
          onClose={closeModal}
          maxW="max-w-2xl"
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Aviso de conflito */}
            {conflito && (
              <div className="bg-amber-400/20 border border-amber-400/40 text-amber-300 rounded-lg px-4 py-3 flex items-start gap-2.5">
                <AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" />
                <span className="text-sm">{conflito}</span>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input label="Título" name="titulo" value={form.titulo} onChange={handleChange} required />
              <Select label="Agenda" name="agenda" value={form.agenda} onChange={handleChange} options={agendasOpts} />
              <Select label="Cliente (opcional)" name="cliente" value={form.cliente} onChange={handleChange} options={clientesOpts} />
            </div>

            {/* Separador */}
            <div className="border-t border-navy-700 my-3" />

            {/* Horário disponível */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-slate-300 flex items-center gap-1.5 mb-1">
                  <Clock size={14} />
                  Horário Disponível
                </label>
                <select
                  name="horario"
                  value={form.horario}
                  onChange={handleChange}
                  disabled={!form.agenda}
                  className="w-full rounded-lg border px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:text-slate-100 dark:focus:ring-violet-500 transition-colors duration-150 border-gray-300 bg-white dark:border-navy-500 dark:bg-navy-800 disabled:opacity-50 disabled:cursor-not-allowed dark:disabled:bg-navy-900"
                >
                  {horarioOpts.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
                <p className="text-xs text-slate-500 mt-1">
                  Vincula este compromisso a um horário com controle de vagas
                </p>
              </div>

              {form.horario && (
                <div>
                  <Input
                    label="Data do Horário"
                    type="date"
                    name="data_horario"
                    value={form.data_horario}
                    onChange={handleChange}
                  />
                  {diaLabel && (
                    <p className="text-xs text-slate-500 mt-1">
                      Deve ser uma {diaLabel}
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Separador + Dados de contato (quando sem cliente) */}
            {!form.cliente && (
              <>
                <div className="border-t border-navy-700 my-3" />
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide flex items-center gap-1.5 mb-3">
                    <User size={12} />
                    Dados de contato
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Input
                      label="Nome do contato"
                      name="nome_contato"
                      value={form.nome_contato}
                      onChange={handleChange}
                    />
                    <Input
                      label="Telefone do contato"
                      type="tel"
                      name="telefone_contato"
                      value={form.telefone_contato}
                      onChange={handleChange}
                      placeholder="(00) 00000-0000"
                    />
                    <Input
                      label="Email (opcional)"
                      type="email"
                      name="email_contato"
                      value={form.email_contato}
                      onChange={handleChange}
                    />
                  </div>
                </div>
              </>
            )}

            {/* Separador + campos existentes */}
            <div className="border-t border-navy-700 my-3" />

            {/* Badge de origem (somente na edição) */}
            {editingId && origemAtual && (
              <div className="mb-2">
                <p className="text-xs text-slate-500 mb-1">Origem</p>
                {origemAtual === 'PUBLICO' ? (
                  <span className="bg-violet-400/15 text-violet-400 border border-violet-400/30 rounded-full px-2 py-0.5 text-xs inline-flex items-center gap-1">
                    <Globe size={10} />
                    Público
                  </span>
                ) : (
                  <span className="bg-navy-600 text-slate-400 rounded-full px-2 py-0.5 text-xs inline-flex items-center gap-1">
                    <Shield size={10} />
                    Interno
                  </span>
                )}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input label="Início" type="datetime-local" name="inicio" value={form.inicio} onChange={handleChange} />
              <Input label="Fim" type="datetime-local" name="fim" value={form.fim} onChange={handleChange} />
              <Input label="Local" type="text" name="local" value={form.local} onChange={handleChange} />
              <Select
                label="Status"
                name="status"
                value={form.status}
                onChange={handleChange}
                options={STATUS_COMPROMISSO}
              />
              <div className="sm:col-span-2">
                <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Descrição</label>
                <textarea
                  name="descricao"
                  value={form.descricao}
                  onChange={handleChange}
                  rows={3}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500 transition-colors duration-150 mt-1"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Observações</label>
                <textarea
                  name="observacoes"
                  value={form.observacoes}
                  onChange={handleChange}
                  rows={2}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500 transition-colors duration-150 mt-1"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={closeModal}>Cancelar</Button>
              <Button type="submit" loading={saving}>{editingId ? 'Salvar Alterações' : 'Criar'}</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

export default function Agendamento() {
  const [tab, setTab] = useState('compromissos')
  const [pendentesCount, setPendentesCount] = useState(0)

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Agendamento</h1>
        <p className="text-sm text-gray-500 mt-0.5 dark:text-slate-400">
          Compromissos e horários — aulas, consultas, atendimentos
        </p>
      </div>

      <div className="flex gap-1 overflow-x-auto pb-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium rounded-lg whitespace-nowrap transition-colors flex items-center gap-1.5 ${
              tab === t.key
                ? 'bg-primary-600 text-white dark:bg-violet-600'
                : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200 dark:bg-navy-800 dark:text-slate-400 dark:hover:bg-navy-700 dark:border-navy-600'
            }`}
          >
            {t.label}
            {t.key === 'pendentes' && pendentesCount > 0 && (
              <span className="bg-amber-400/30 text-amber-400 rounded-full px-1.5 py-0.5 text-[10px] font-bold leading-none">
                {pendentesCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {tab === 'compromissos' && <CompromissosTab />}

      {tab === 'agendas' && (
        <ResourceCrud
          resource="agendamento/agendas"
          title="Agendas"
          createLabel="+ Nova Agenda"
          emptyIcon="🗓️"
          emptyText="Nenhuma agenda cadastrada."
          titleField="nome"
          columns={[
            { key: 'nome', label: 'Nome' },
            { key: 'profissional_nome', label: 'Profissional' },
            { key: 'cor', label: 'Cor' },
            { key: 'ativo', label: 'Ativa', boolean: true },
          ]}
          fields={[
            { name: 'nome', label: 'Nome', type: 'text' },
            {
              name: 'profissional',
              label: 'Profissional responsável',
              type: 'select-remote',
              endpoint: 'accounts/usuarios',
              labelField: 'nome_completo',
              params: { perfil: 'PROFISSIONAL' },
              filterOptions: (u) => u.perfil === 'PROFISSIONAL',
            },
            { name: 'cor', label: 'Cor (hex)', type: 'text', placeholder: '#3B82F6' },
            { name: 'descricao', label: 'Descrição', type: 'textarea' },
            { name: 'ativo', label: 'Ativa', type: 'checkbox' },
            { name: 'permite_agendamento_publico', label: 'Permitir agendamento público', type: 'checkbox' },
          ]}
          emptyForm={{ nome: '', profissional: '', cor: '#3B82F6', descricao: '', ativo: true, permite_agendamento_publico: false }}
        />
      )}

      {tab === 'calendario' && <CalendarioTab />}

      {tab === 'horarios' && <HorariosTab />}

      {tab === 'pendentes' && (
        <PendentesTab onCountChange={setPendentesCount} />
      )}
    </div>
  )
}

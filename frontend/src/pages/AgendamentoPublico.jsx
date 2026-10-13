/**
 * Página pública /agendar/:slug
 * Sem autenticação, sem AppLayout, sem tokenRef.
 * Mobile-first 375px, dark mode navy/violet.
 */
import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import {
  ChevronLeft, ChevronRight, Users, Clock,
  CheckCircle, AlertTriangle, CalendarCheck,
} from 'lucide-react'

// Cliente público sem token (axios direto, sem interceptor de auth)
const publicApi = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

const DIAS_ABREV = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
const MESES = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
]
const MESES_ABREV = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

function pad2(n) {
  return String(n).padStart(2, '0')
}

function dataParaISO(d) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

function inicioSemana(data) {
  const d = new Date(data)
  const dia = d.getDay() // 0=Dom
  d.setDate(d.getDate() - dia)
  d.setHours(0, 0, 0, 0)
  return d
}

function formatarDataLonga(isoStr) {
  const [y, m, d] = isoStr.split('-').map(Number)
  const data = new Date(y, m - 1, d)
  const diaSemana = DIAS_ABREV[data.getDay()]
  return `${diaSemana}, ${d} de ${MESES[m - 1]} de ${y}`
}

// Componente Input leve para a página pública
function InputPublico({ label, error, required, ...props }) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-sm font-medium text-slate-300">
          {label}{required && <span className="text-red-400 ml-0.5">*</span>}
        </label>
      )}
      <input
        className={`w-full rounded-lg border px-3 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-colors duration-150 bg-navy-800 ${
          error ? 'border-red-500' : 'border-navy-500'
        }`}
        {...props}
      />
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  )
}

export default function AgendamentoPublico() {
  const { slug } = useParams()

  // Info da agenda (nome, descrição, cor)
  const [agendaInfo, setAgendaInfo] = useState(null)
  const [agendaErro, setAgendaErro] = useState(null)

  // Semana exibida
  const [semanaInicio, setSemanaInicio] = useState(() => inicioSemana(new Date()))

  // Dia selecionado
  const [dataSelecionada, setDataSelecionada] = useState(dataParaISO(new Date()))

  // Slots do dia
  const [slots, setSlots] = useState([])
  const [loadingSlots, setLoadingSlots] = useState(false)

  // Slot clicado
  const [slotSelecionado, setSlotSelecionado] = useState(null)

  // Formulário
  const [nome, setNome] = useState('')
  const [telefone, setTelefone] = useState('')
  const [email, setEmail] = useState('')
  const [formErrors, setFormErrors] = useState({})

  // Estados de envio
  const [enviando, setEnviando] = useState(false)
  const [confirmado, setConfirmado] = useState(false)
  const [confirmacaoInfo, setConfirmacaoInfo] = useState(null)
  const [erro, setErro] = useState(null)

  // Carregar info da agenda (usa o endpoint de disponibilidade com range de 1 dia
  // para obter os dados da agenda; se der 404, mostra erro)
  // Na verdade, não há endpoint público só de info da agenda.
  // Usamos o endpoint de disponibilidade para validar que a agenda existe.
  const carregarAgendaInfo = useCallback(async () => {
    try {
      // Tenta buscar disponibilidade de hoje — se agenda não existir/pública → 404
      const hoje = dataParaISO(new Date())
      await publicApi.get(`/publico/agenda/${slug}/disponibilidade/`, {
        params: { de: hoje, ate: hoje },
      })
      // Agenda existe e é pública — não temos nome via API pública ainda,
      // então usamos o slug formatado como título
      setAgendaInfo({ nome: slug.replace(/-/g, ' '), descricao: '', cor: '#7c3aed' })
    } catch (err) {
      if (err.response?.status === 404) {
        setAgendaErro('Agenda não encontrada ou não disponível para agendamento público.')
      } else {
        setAgendaErro('Erro ao carregar agenda. Tente novamente.')
      }
    }
  }, [slug])

  useEffect(() => {
    carregarAgendaInfo()
  }, [carregarAgendaInfo])

  const carregarSlots = useCallback(async (data) => {
    setLoadingSlots(true)
    setSlots([])
    setSlotSelecionado(null)
    setErro(null)
    try {
      const r = await publicApi.get(`/publico/agenda/${slug}/disponibilidade/`, {
        params: { de: data, ate: data },
      })
      setSlots(r.data)
    } catch {
      setSlots([])
    } finally {
      setLoadingSlots(false)
    }
  }, [slug])

  useEffect(() => {
    carregarSlots(dataSelecionada)
  }, [carregarSlots, dataSelecionada])

  // Dias da semana atual
  const diasDaSemana = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(semanaInicio)
    d.setDate(semanaInicio.getDate() + i)
    return d
  })

  const semanaAnterior = () => {
    const d = new Date(semanaInicio)
    d.setDate(d.getDate() - 7)
    setSemanaInicio(d)
  }

  const proximaSemana = () => {
    const d = new Date(semanaInicio)
    d.setDate(d.getDate() + 7)
    setSemanaInicio(d)
  }

  const hoje = dataParaISO(new Date())

  const validarForm = () => {
    const errs = {}
    if (!nome.trim()) errs.nome = 'Obrigatório'
    if (!telefone.trim()) errs.telefone = 'Obrigatório'
    return errs
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errs = validarForm()
    if (Object.keys(errs).length > 0) { setFormErrors(errs); return }
    if (!slotSelecionado) return

    setEnviando(true)
    setErro(null)
    try {
      await publicApi.post(`/publico/agenda/${slug}/agendar/`, {
        horario_id: slotSelecionado.horario_id,
        data_horario: dataSelecionada,
        nome_contato: nome.trim(),
        telefone_contato: telefone.trim(),
        email_contato: email.trim(),
      })
      setConfirmacaoInfo({
        data: formatarDataLonga(dataSelecionada),
        hora: slotSelecionado.hora_inicio,
        servico: slotSelecionado.servico,
        duracao: slotSelecionado.duracao_minutos,
      })
      setConfirmado(true)
    } catch (err) {
      const status = err.response?.status
      const data = err.response?.data
      if (status === 400 && data?.erro?.includes('vagas')) {
        setErro('Este horário foi preenchido. Escolha outro.')
        setSlotSelecionado(null)
        carregarSlots(dataSelecionada)
      } else if (status === 400 && data?.erro) {
        setErro(data.erro)
      } else if (status === 429) {
        setErro('Muitas tentativas. Aguarde antes de tentar novamente.')
      } else {
        setErro('Algo deu errado. Tente novamente em instantes.')
      }
    } finally {
      setEnviando(false)
    }
  }

  const resetar = () => {
    setConfirmado(false)
    setConfirmacaoInfo(null)
    setSlotSelecionado(null)
    setNome('')
    setTelefone('')
    setEmail('')
    setFormErrors({})
    setErro(null)
    carregarSlots(dataSelecionada)
  }

  // Adicionar classe dark ao root da página
  useEffect(() => {
    document.documentElement.classList.add('dark')
    return () => {
      // Não remover — o resto da app já tem dark mode
    }
  }, [])

  if (agendaErro) {
    return (
      <div className="min-h-screen bg-navy-950 text-slate-100 font-body flex items-center justify-center px-4">
        <div className="text-center max-w-sm">
          <AlertTriangle size={40} className="text-red-400 mx-auto mb-3" />
          <p className="text-slate-300 text-sm">{agendaErro}</p>
        </div>
      </div>
    )
  }

  if (!agendaInfo) {
    return (
      <div className="min-h-screen bg-navy-950 text-slate-100 font-body flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-violet-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-navy-950 text-slate-100 font-body">
      {/* Header */}
      <header className="px-4 pt-8 pb-6 max-w-lg mx-auto">
        <div className="flex items-center gap-2 mb-1">
          <span
            className="w-3 h-3 rounded-full inline-block"
            style={{ backgroundColor: agendaInfo.cor || '#7c3aed' }}
          />
          <h1 className="text-xl font-bold text-slate-100 capitalize">{agendaInfo.nome}</h1>
        </div>
        {agendaInfo.descricao && (
          <p className="text-sm text-slate-400 mt-1">{agendaInfo.descricao}</p>
        )}
        <div className="border-b border-navy-700 mt-6" />
      </header>

      {confirmado ? (
        /* Estado de sucesso */
        <main className="flex flex-col items-center justify-center text-center px-6 py-16 max-w-sm mx-auto">
          <CheckCircle size={56} className="text-emerald-400 mb-4" />
          <h2 className="text-xl font-bold text-slate-100">Agendamento confirmado!</h2>
          {confirmacaoInfo && (
            <>
              <p className="text-sm text-slate-300 mt-2">{confirmacaoInfo.data}</p>
              <p className="text-sm text-slate-300">
                {confirmacaoInfo.hora} — {confirmacaoInfo.servico || 'Serviço'}{confirmacaoInfo.duracao ? ` ${confirmacaoInfo.duracao}min` : ''}
              </p>
            </>
          )}
          <p className="text-sm text-slate-500 mt-3">
            Anote o horário ou tire um print desta tela como comprovante.
          </p>
          <button
            onClick={resetar}
            className="mt-6 px-4 py-2 text-sm font-medium rounded-lg bg-navy-800 border border-navy-600 text-slate-300 hover:bg-navy-700 transition-colors"
          >
            Fazer outro agendamento
          </button>
        </main>
      ) : (
        <main>
          {/* Seletor de data (semana) */}
          <section className="px-4 py-4 max-w-lg mx-auto">
            <div className="flex items-center justify-between gap-2">
              <button
                onClick={semanaAnterior}
                className="w-8 h-8 rounded-lg bg-navy-800 hover:bg-navy-700 border border-navy-600 flex items-center justify-center text-slate-400 hover:text-slate-200 transition-colors shrink-0"
              >
                <ChevronLeft size={16} />
              </button>

              <div className="flex gap-1.5 overflow-x-auto py-1 flex-1 justify-center">
                {diasDaSemana.map((d) => {
                  const iso = dataParaISO(d)
                  const ativo = iso === dataSelecionada
                  const eHoje = iso === hoje
                  return (
                    <button
                      key={iso}
                      onClick={() => setDataSelecionada(iso)}
                      className={`min-w-[52px] flex flex-col items-center gap-0.5 rounded-xl px-2 py-2 text-center cursor-pointer transition-colors shrink-0 ${
                        ativo
                          ? 'bg-violet-600 border border-violet-600'
                          : 'bg-navy-800 hover:bg-navy-700 border border-navy-600'
                      }`}
                    >
                      <span className={`text-xs uppercase tracking-wide ${ativo ? 'text-violet-200' : 'text-slate-500'}`}>
                        {DIAS_ABREV[d.getDay()]}
                      </span>
                      <span className={`text-base font-semibold ${ativo ? 'text-white' : 'text-slate-300'}`}>
                        {d.getDate()}
                      </span>
                      {eHoje && (
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mx-auto" />
                      )}
                    </button>
                  )
                })}
              </div>

              <button
                onClick={proximaSemana}
                className="w-8 h-8 rounded-lg bg-navy-800 hover:bg-navy-700 border border-navy-600 flex items-center justify-center text-slate-400 hover:text-slate-200 transition-colors shrink-0"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </section>

          {/* Lista de horários */}
          <section className="px-4 max-w-lg mx-auto space-y-2 mt-2">
            {loadingSlots ? (
              <div className="flex justify-center py-8">
                <div className="w-6 h-6 border-2 border-violet-600 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : slots.length === 0 ? (
              <div className="text-center py-8 space-y-2">
                <Clock size={28} className="text-slate-600 mx-auto" />
                <p className="text-sm text-slate-500">Nenhum horário disponível neste dia.</p>
              </div>
            ) : (
              slots.map((slot) => {
                const lotado = slot.lotado
                const selecionado = slotSelecionado?.horario_id === slot.horario_id

                if (lotado) {
                  return (
                    <div
                      key={`${slot.horario_id}-${slot.data}`}
                      className="bg-navy-900 border border-navy-700 rounded-xl px-4 py-3.5 flex items-center justify-between opacity-60 cursor-not-allowed"
                    >
                      <div>
                        <p className="text-base font-bold text-slate-500">{slot.hora_inicio}</p>
                        <p className="text-sm text-slate-600 mt-0.5">{slot.servico || 'Serviço'}</p>
                        <p className="text-xs text-slate-600">{slot.duracao_minutos}min</p>
                      </div>
                      <span className="bg-red-400/10 text-red-400 rounded-full px-2 py-0.5 text-xs">
                        Lotado
                      </span>
                    </div>
                  )
                }

                return (
                  <button
                    key={`${slot.horario_id}-${slot.data}`}
                    onClick={() => {
                      setSlotSelecionado(selecionado ? null : slot)
                      setErro(null)
                    }}
                    className={`w-full text-left rounded-xl px-4 py-3.5 flex items-center justify-between transition-all duration-150 ${
                      selecionado
                        ? 'bg-violet-700/40 border-2 border-violet-500'
                        : 'bg-navy-800 hover:bg-violet-700/60 border border-navy-600 hover:border-violet-500 cursor-pointer'
                    }`}
                  >
                    <div className="flex-1">
                      <p className="text-base font-bold text-slate-100">{slot.hora_inicio}</p>
                      <p className="text-sm text-slate-300 mt-0.5">{slot.servico || 'Serviço'}</p>
                      <p className="text-xs text-slate-500">{slot.duracao_minutos}min</p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      {selecionado && (
                        <CheckCircle size={14} className="text-violet-400" />
                      )}
                      <span className="flex items-center gap-1 text-xs text-emerald-400">
                        <Users size={12} />
                        {slot.vagas_disponiveis} vaga{slot.vagas_disponiveis !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </button>
                )
              })
            )}
          </section>

          {/* Formulário de contato (aparece ao clicar num slot) */}
          {slotSelecionado && (
            <section className="px-4 max-w-lg mx-auto mt-4">
              <div className="bg-navy-800 border border-navy-600 rounded-xl p-4">
                {/* Cabeçalho do slot selecionado */}
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">
                      Horário selecionado
                    </p>
                    <p className="text-sm text-slate-200 mt-1">
                      {formatarDataLonga(dataSelecionada)} • {slotSelecionado.hora_inicio}
                      {slotSelecionado.servico ? ` • ${slotSelecionado.servico}` : ''}
                      {` ${slotSelecionado.duracao_minutos}min`}
                    </p>
                  </div>
                  <button
                    onClick={() => setSlotSelecionado(null)}
                    className="text-slate-500 hover:text-slate-300 text-lg leading-none ml-2"
                  >
                    &times;
                  </button>
                </div>

                {/* Campos */}
                <form onSubmit={handleSubmit} className="space-y-3 mt-4">
                  <InputPublico
                    label="Seu nome"
                    placeholder="Como você prefere ser chamado(a)?"
                    value={nome}
                    onChange={(e) => { setNome(e.target.value); setFormErrors(p => ({ ...p, nome: '' })) }}
                    required
                    error={formErrors.nome}
                  />
                  <div>
                    <InputPublico
                      label="Telefone"
                      type="tel"
                      placeholder="(00) 00000-0000"
                      value={telefone}
                      onChange={(e) => { setTelefone(e.target.value); setFormErrors(p => ({ ...p, telefone: '' })) }}
                      required
                      error={formErrors.telefone}
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      Usaremos para confirmar seu agendamento
                    </p>
                  </div>
                  <InputPublico
                    label="Email (opcional)"
                    type="email"
                    placeholder="seu@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />

                  {/* Erro inline */}
                  {erro && (
                    <div className="bg-red-400/10 border border-red-400/30 rounded-xl px-4 py-3 flex items-start gap-2.5">
                      <AlertTriangle size={16} className="text-red-400 shrink-0 mt-0.5" />
                      <p className="text-sm text-red-300">{erro}</p>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={enviando}
                    className="w-full mt-4 px-6 py-3 text-base font-medium rounded-lg bg-violet-600 hover:bg-violet-500 text-white flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {enviando ? (
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <CalendarCheck size={16} />
                    )}
                    Confirmar Agendamento
                  </button>
                  <p className="text-xs text-slate-600 text-center mt-2">
                    Seus dados são usados apenas para confirmar seu agendamento.
                  </p>
                </form>
              </div>
            </section>
          )}

          {/* Erro fora do formulário (ex: slot lotado após não ter slot selecionado) */}
          {erro && !slotSelecionado && (
            <section className="px-4 max-w-lg mx-auto mt-4">
              <div className="bg-red-400/10 border border-red-400/30 rounded-xl px-4 py-3 flex items-start gap-2.5">
                <AlertTriangle size={16} className="text-red-400 shrink-0 mt-0.5" />
                <p className="text-sm text-red-300">{erro}</p>
              </div>
            </section>
          )}
        </main>
      )}

      <footer className="text-center py-6 mt-8 border-t border-navy-800">
        <p className="text-xs text-slate-700">Powered by UidCore</p>
      </footer>
    </div>
  )
}

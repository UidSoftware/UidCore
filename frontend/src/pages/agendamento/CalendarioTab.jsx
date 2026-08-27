import { useState, useEffect, useMemo, useCallback } from 'react'
import api from '../../api/client.js'
import { extractErrorMessage } from '../../utils/errors.js'
import Card from '../../components/ui/Card.jsx'
import ResourceCrud from '../../components/ui/ResourceCrud.jsx'
import { STATUS_COMPROMISSO } from '../Agendamento.jsx'

const DIAS_SEMANA = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
const MESES = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]

// Máximo de indicadores de Agenda exibidos por célula do grid — acima
// disso, exibe "+N" (RF03). Um único limite para mobile/desktop mantém a
// implementação simples sem depender de lógica de breakpoint em JS.
const LIMITE_INDICADORES = 4

const pad2 = (n) => String(n).padStart(2, '0')

// Chave 'YYYY-MM-DD' em horário LOCAL (nunca toISOString, que converte
// para UTC e pode deslocar o dia perto da virada de fuso).
function dataParaChave(date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`
}

function formatarHora(date) {
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`
}

const emptyFormCompromisso = {
  titulo: '', agenda: '', cliente: '', inicio: '', fim: '', local: '',
  status: 'AGENDADO', descricao: '', observacoes: '',
}

export default function CalendarioTab() {
  const hoje = new Date()
  const [mesAtual, setMesAtual] = useState(new Date(hoje.getFullYear(), hoje.getMonth(), 1))
  const [diaSelecionado, setDiaSelecionado] = useState(null)
  const [compromissos, setCompromissos] = useState([])
  const [agendas, setAgendas] = useState([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState(null)
  const [compromissoEditando, setCompromissoEditando] = useState(null)

  const fetchCompromissos = useCallback(async () => {
    setLoading(true)
    setErro(null)
    try {
      const response = await api.get('/agendamento/compromissos/', {
        params: { page_size: 500, ordering: 'inicio' },
      })
      setCompromissos(response.data.results)
    } catch (error) {
      setErro(extractErrorMessage(error, 'Erro ao carregar compromissos.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCompromissos()
  }, [fetchCompromissos])

  useEffect(() => {
    api.get('/agendamento/agendas/', { params: { page_size: 200 } })
      .then((response) => setAgendas(response.data.results))
      .catch(() => setAgendas([]))
  }, [])

  const agendaMap = useMemo(() => {
    const map = {}
    for (const a of agendas) map[a.id] = a
    return map
  }, [agendas])

  // Agrupa compromissos por dia (RN02: inicio nulo é excluído do
  // agrupamento, mas nunca removido de `compromissos`).
  const compromissosPorDia = useMemo(() => {
    const map = {}
    for (const c of compromissos) {
      if (!c.inicio) continue
      const chave = dataParaChave(new Date(c.inicio))
      if (!map[chave]) map[chave] = []
      map[chave].push(c)
    }
    return map
  }, [compromissos])

  const ano = mesAtual.getFullYear()
  const mes = mesAtual.getMonth()
  const monthLabel = `${MESES[mes]} ${ano}`

  const celulas = useMemo(() => {
    const primeiroDiaSemana = new Date(ano, mes, 1).getDay()
    const totalDias = new Date(ano, mes + 1, 0).getDate()
    const lista = []
    for (let i = 0; i < primeiroDiaSemana; i++) {
      lista.push(null)
    }
    for (let dia = 1; dia <= totalDias; dia++) {
      const data = new Date(ano, mes, dia)
      lista.push({ dia, chave: dataParaChave(data) })
    }
    return lista
  }, [ano, mes])

  const irParaMesAnterior = () => {
    setMesAtual(new Date(ano, mes - 1, 1))
    setDiaSelecionado(null)
  }

  const irParaMesSeguinte = () => {
    setMesAtual(new Date(ano, mes + 1, 1))
    setDiaSelecionado(null)
  }

  const toggleDia = (chave) => {
    setDiaSelecionado((atual) => (atual === chave ? null : chave))
  }

  const chaveHoje = dataParaChave(hoje)
  const compromissosDoDia = diaSelecionado ? (compromissosPorDia[diaSelecionado] || []) : []

  const formatarDataLonga = (chave) => {
    const [y, m, d] = chave.split('-').map(Number)
    return `${d} de ${MESES[m - 1].toLowerCase()} de ${y}`
  }

  const handleFecharEdicao = () => {
    setCompromissoEditando(null)
    fetchCompromissos()
  }

  return (
    <div className="space-y-4">
      {/* Navegação de mês (RF02) */}
      <div className="flex items-center justify-between gap-3 mb-1">
        <button
          onClick={irParaMesAnterior}
          className="px-3 py-1.5 text-sm font-medium rounded-lg bg-white text-gray-600 hover:bg-gray-100 border border-gray-200 dark:bg-navy-800 dark:text-slate-400 dark:hover:bg-navy-700 dark:border-navy-600"
        >
          <span className="hidden sm:inline">‹ Mês anterior</span>
          <span className="sm:hidden">‹</span>
        </button>
        <h2 className="text-base font-semibold text-gray-900 dark:text-slate-100 capitalize">
          {monthLabel}
        </h2>
        <button
          onClick={irParaMesSeguinte}
          className="px-3 py-1.5 text-sm font-medium rounded-lg bg-white text-gray-600 hover:bg-gray-100 border border-gray-200 dark:bg-navy-800 dark:text-slate-400 dark:hover:bg-navy-700 dark:border-navy-600"
        >
          <span className="hidden sm:inline">Mês seguinte ›</span>
          <span className="sm:hidden">›</span>
        </button>
      </div>

      {erro && (
        <div className="text-sm text-red-600 dark:text-red-400">{erro}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-12 text-gray-400 dark:text-slate-500 text-sm">Carregando...</div>
      ) : (
        <>
          {/* Grid mensal (RF02, RF03, RF04, RF06) */}
          <div className="grid grid-cols-7 gap-1 sm:gap-2">
            {DIAS_SEMANA.map((d) => (
              <div key={d} className="text-center text-xs font-semibold text-gray-400 dark:text-slate-500 pb-1">
                {d}
              </div>
            ))}

            {celulas.map((celula, idx) => {
              if (!celula) return <div key={`vazio-${idx}`} />

              const compromissosDaCelula = compromissosPorDia[celula.chave] || []
              const ehHoje = celula.chave === chaveHoje
              const ehSelecionado = celula.chave === diaSelecionado

              const agendaIdsDistintas = [
                ...new Set(compromissosDaCelula.map((c) => c.agenda ?? 'sem-agenda')),
              ]
              const indicadoresVisiveis = agendaIdsDistintas.slice(0, LIMITE_INDICADORES)
              const extra = agendaIdsDistintas.length - indicadoresVisiveis.length

              let estadoClasses = 'bg-white border-gray-200 hover:bg-gray-50 dark:bg-navy-800 dark:border-navy-700 dark:hover:bg-navy-700/60'
              if (ehSelecionado) {
                estadoClasses = 'bg-primary-50 border-primary-300 dark:bg-violet-900/20 dark:border-violet-600'
              }
              if (ehHoje) {
                estadoClasses += ' ring-2 ring-primary-500 dark:ring-violet-500'
              }

              return (
                <button
                  key={celula.chave}
                  onClick={() => toggleDia(celula.chave)}
                  className={`aspect-square sm:aspect-auto sm:h-20 flex flex-col items-start p-1.5 sm:p-2 rounded-lg border text-left transition-colors ${estadoClasses}`}
                >
                  <span className="text-xs sm:text-sm font-medium text-gray-700 dark:text-slate-300">
                    {celula.dia}
                  </span>
                  <div className="flex flex-wrap items-center gap-0.5 mt-auto">
                    {indicadoresVisiveis.map((agendaId) => {
                      const agenda = agendaId !== 'sem-agenda' ? agendaMap[agendaId] : null
                      const cor = agenda?.cor
                      return (
                        <span
                          key={agendaId}
                          className={`w-1.5 h-1.5 rounded-full shrink-0 ${!cor ? 'bg-gray-400 dark:bg-slate-500' : ''}`}
                          style={cor ? { backgroundColor: cor } : undefined}
                        />
                      )
                    })}
                    {extra > 0 && (
                      <span className="text-[10px] leading-none text-gray-400 dark:text-slate-500 font-medium">
                        +{extra}
                      </span>
                    )}
                  </div>
                </button>
              )
            })}
          </div>

          {/* Lista do dia selecionado (RF04, RF05) */}
          {diaSelecionado && (
            <Card className="mt-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">
                  {formatarDataLonga(diaSelecionado)}
                </h3>
                <span className="text-xs text-gray-400 dark:text-slate-500">
                  {compromissosDoDia.length} compromisso(s)
                </span>
              </div>

              {compromissosDoDia.length === 0 ? (
                <p className="text-sm text-gray-400 dark:text-slate-500 py-4 text-center">
                  Nenhum compromisso neste dia.
                </p>
              ) : (
                <div>
                  {compromissosDoDia.map((compromisso) => {
                    const agenda = compromisso.agenda ? agendaMap[compromisso.agenda] : null
                    const cor = agenda?.cor
                    const inicioDate = new Date(compromisso.inicio)
                    const horaInicio = formatarHora(inicioDate)
                    const horaFim = compromisso.fim ? formatarHora(new Date(compromisso.fim)) : null

                    return (
                      <button
                        key={compromisso.id}
                        onClick={() => setCompromissoEditando(compromisso)}
                        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left hover:bg-gray-50 dark:hover:bg-navy-700/60 transition-colors border-b border-gray-100 dark:border-navy-700 last:border-b-0"
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full shrink-0 ${!cor ? 'bg-gray-400 dark:bg-slate-500' : ''}`}
                          style={cor ? { backgroundColor: cor } : undefined}
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 dark:text-slate-100 truncate">
                            {compromisso.titulo}
                          </p>
                          <p className="text-xs text-gray-400 dark:text-slate-500">
                            {horaInicio}{horaFim ? `–${horaFim}` : ''}
                          </p>
                        </div>
                        <span className="text-xs bg-primary-50 text-primary-700 rounded-full px-2 py-0.5 font-medium dark:bg-violet-900/30 dark:text-violet-300 shrink-0">
                          {compromisso.status_label}
                        </span>
                      </button>
                    )
                  })}
                </div>
              )}
            </Card>
          )}
        </>
      )}

      {/* Reaproveita o MESMO modal de edição de Compromisso já usado na
          aba "Compromissos" — sem tabela visível (hideList), só o modal
          é exibido, aberto via externalEditItem (RF05, §7.2). */}
      <ResourceCrud
        resource="agendamento/compromissos"
        title="Compromisso"
        createLabel="+ Novo Compromisso"
        titleField="titulo"
        hideList
        columns={[]}
        fields={[
          { name: 'titulo', label: 'Título', type: 'text' },
          { name: 'agenda', label: 'Agenda', type: 'select-remote', endpoint: 'agendamento/agendas', labelField: 'nome' },
          { name: 'cliente', label: 'Cliente (opcional)', type: 'select-remote', endpoint: 'clientes', labelField: 'nome_razao_social' },
          { name: 'inicio', label: 'Início', type: 'datetime-local' },
          { name: 'fim', label: 'Fim', type: 'datetime-local' },
          { name: 'local', label: 'Local', type: 'text' },
          { name: 'status', label: 'Status', type: 'select', options: STATUS_COMPROMISSO },
          { name: 'descricao', label: 'Descrição', type: 'textarea' },
          { name: 'observacoes', label: 'Observações', type: 'textarea' },
        ]}
        emptyForm={emptyFormCompromisso}
        externalEditItem={compromissoEditando}
        onExternalEditClose={handleFecharEdicao}
      />
    </div>
  )
}

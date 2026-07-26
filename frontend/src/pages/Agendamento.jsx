import { useState } from 'react'
import ResourceCrud from '../components/ui/ResourceCrud.jsx'

const TABS = [
  { key: 'compromissos', label: 'Compromissos' },
  { key: 'agendas', label: 'Agendas' },
]

const STATUS_COMPROMISSO = [
  { value: 'AGENDADO', label: 'Agendado' },
  { value: 'CONFIRMADO', label: 'Confirmado' },
  { value: 'CANCELADO', label: 'Cancelado' },
  { value: 'CONCLUIDO', label: 'Concluído' },
]

export default function Agendamento() {
  const [tab, setTab] = useState('compromissos')

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Agendamento</h1>
        <p className="text-sm text-gray-500 mt-0.5">Compromissos e horários — aulas, consultas, atendimentos</p>
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

      {tab === 'compromissos' && (
        <ResourceCrud
          resource="agendamento/compromissos"
          title="Compromissos"
          createLabel="+ Novo Compromisso"
          emptyIcon="📅"
          emptyText="Nenhum compromisso encontrado."
          titleField="titulo"
          columns={[
            { key: 'titulo', label: 'Título' },
            { key: 'agenda_nome', label: 'Agenda' },
            { key: 'cliente_nome', label: 'Cliente' },
            { key: 'inicio', label: 'Início', datetime: true },
            { key: 'status_label', label: 'Status', badge: true },
          ]}
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
          emptyForm={{ titulo: '', agenda: '', cliente: '', inicio: '', fim: '', local: '', status: 'AGENDADO', descricao: '', observacoes: '' }}
        />
      )}

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
            { key: 'cor', label: 'Cor' },
            { key: 'ativo', label: 'Ativa', boolean: true },
          ]}
          fields={[
            { name: 'nome', label: 'Nome', type: 'text' },
            { name: 'cor', label: 'Cor (hex)', type: 'text', placeholder: '#3B82F6' },
            { name: 'descricao', label: 'Descrição', type: 'textarea' },
            { name: 'ativo', label: 'Ativa', type: 'checkbox' },
          ]}
          emptyForm={{ nome: '', cor: '#3B82F6', descricao: '', ativo: true }}
        />
      )}
    </div>
  )
}

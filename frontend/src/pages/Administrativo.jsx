import { useState } from 'react'
import ResourceCrud from '../components/ui/ResourceCrud.jsx'

const TABS = [
  { key: 'documentos', label: 'Documentos' },
  { key: 'tipos', label: 'Tipos de Documento' },
]

const STATUS_DOCUMENTO = [
  { value: 'RASCUNHO', label: 'Rascunho' },
  { value: 'VIGENTE', label: 'Vigente' },
  { value: 'EXPIRADO', label: 'Expirado' },
  { value: 'CANCELADO', label: 'Cancelado' },
]

export default function Administrativo() {
  const [tab, setTab] = useState('documentos')

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Administrativo</h1>
        <p className="text-sm text-gray-500 mt-0.5">Documentos, contratos e processos internos</p>
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

      {tab === 'documentos' && (
        <ResourceCrud
          resource="administrativo/documentos"
          title="Documentos"
          createLabel="+ Novo Documento"
          emptyIcon="📁"
          emptyText="Nenhum documento encontrado."
          titleField="titulo"
          columns={[
            { key: 'titulo', label: 'Título' },
            { key: 'tipo_nome', label: 'Tipo' },
            { key: 'cliente_nome', label: 'Cliente' },
            { key: 'status_label', label: 'Status', badge: true },
            { key: 'validade', label: 'Validade', date: true },
          ]}
          fields={[
            { name: 'titulo', label: 'Título', type: 'text' },
            { name: 'tipo', label: 'Tipo de Documento', type: 'select-remote', endpoint: 'administrativo/tipos', labelField: 'nome' },
            { name: 'arquivo', label: 'Arquivo', type: 'file' },
            { name: 'cliente', label: 'Cliente (opcional)', type: 'select-remote', endpoint: 'clientes', labelField: 'nome_razao_social' },
            { name: 'status', label: 'Status', type: 'select', options: STATUS_DOCUMENTO },
            { name: 'validade', label: 'Validade', type: 'date' },
            { name: 'descricao', label: 'Descrição', type: 'textarea' },
          ]}
          emptyForm={{ titulo: '', tipo: '', arquivo: null, cliente: '', status: 'RASCUNHO', validade: '', descricao: '' }}
        />
      )}

      {tab === 'tipos' && (
        <ResourceCrud
          resource="administrativo/tipos"
          title="Tipos de Documento"
          createLabel="+ Novo Tipo"
          emptyIcon="🏷️"
          emptyText="Nenhum tipo cadastrado."
          titleField="nome"
          columns={[
            { key: 'nome', label: 'Nome' },
            { key: 'descricao', label: 'Descrição' },
          ]}
          fields={[
            { name: 'nome', label: 'Nome', type: 'text' },
            { name: 'descricao', label: 'Descrição', type: 'textarea' },
          ]}
          emptyForm={{ nome: '', descricao: '' }}
        />
      )}
    </div>
  )
}

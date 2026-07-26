import { useState } from 'react'
import ResourceCrud from '../components/ui/ResourceCrud.jsx'

const TABS = [
  { key: 'orcamentos', label: 'Orçamentos' },
  { key: 'pedidos', label: 'Pedidos' },
  { key: 'itens', label: 'Itens de Pedido' },
]

const STATUS_ORCAMENTO = [
  { value: 'RASCUNHO', label: 'Rascunho' },
  { value: 'ENVIADO', label: 'Enviado' },
  { value: 'APROVADO', label: 'Aprovado' },
  { value: 'REJEITADO', label: 'Rejeitado' },
  { value: 'CANCELADO', label: 'Cancelado' },
]

const STATUS_PEDIDO = [
  { value: 'PENDENTE', label: 'Pendente' },
  { value: 'CONFIRMADO', label: 'Confirmado' },
  { value: 'EM_PRODUCAO', label: 'Em Produção' },
  { value: 'ENTREGUE', label: 'Entregue' },
  { value: 'CANCELADO', label: 'Cancelado' },
]

export default function Vendas() {
  const [tab, setTab] = useState('orcamentos')

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Vendas</h1>
        <p className="text-sm text-gray-500 mt-0.5">Orçamentos, pedidos e funil comercial</p>
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

      {tab === 'orcamentos' && (
        <ResourceCrud
          resource="vendas/orcamentos"
          title="Orçamentos"
          createLabel="+ Novo Orçamento"
          emptyIcon="📄"
          emptyText="Nenhum orçamento encontrado."
          titleField="numero"
          columns={[
            { key: 'numero', label: 'Número' },
            { key: 'cliente_nome', label: 'Cliente' },
            { key: 'valor_total', label: 'Valor', money: true },
            { key: 'status_label', label: 'Status', badge: true },
            { key: 'validade', label: 'Validade', date: true },
          ]}
          fields={[
            { name: 'cliente', label: 'Cliente', type: 'select-remote', endpoint: 'clientes', labelField: 'nome_razao_social' },
            { name: 'valor_total', label: 'Valor Total (R$)', type: 'number', step: '0.01', min: '0' },
            { name: 'status', label: 'Status', type: 'select', options: STATUS_ORCAMENTO },
            { name: 'validade', label: 'Validade', type: 'date' },
            { name: 'descricao', label: 'Descrição', type: 'textarea' },
            { name: 'observacoes', label: 'Observações', type: 'textarea' },
          ]}
          emptyForm={{ cliente: '', valor_total: '', status: 'RASCUNHO', validade: '', descricao: '', observacoes: '' }}
        />
      )}

      {tab === 'pedidos' && (
        <ResourceCrud
          resource="vendas/pedidos"
          title="Pedidos"
          createLabel="+ Novo Pedido"
          emptyIcon="🛒"
          emptyText="Nenhum pedido encontrado."
          titleField="numero"
          columns={[
            { key: 'numero', label: 'Número' },
            { key: 'cliente_nome', label: 'Cliente' },
            { key: 'valor_total', label: 'Valor', money: true },
            { key: 'status_label', label: 'Status', badge: true },
            { key: 'data_entrega_prevista', label: 'Entrega prevista', date: true },
          ]}
          fields={[
            { name: 'cliente', label: 'Cliente', type: 'select-remote', endpoint: 'clientes', labelField: 'nome_razao_social' },
            { name: 'valor_total', label: 'Valor Total (R$)', type: 'number', step: '0.01', min: '0' },
            { name: 'status', label: 'Status', type: 'select', options: STATUS_PEDIDO },
            { name: 'data_pedido', label: 'Data do Pedido', type: 'date' },
            { name: 'data_entrega_prevista', label: 'Entrega Prevista', type: 'date' },
            { name: 'observacoes', label: 'Observações', type: 'textarea' },
          ]}
          emptyForm={{ cliente: '', valor_total: '', status: 'PENDENTE', data_pedido: '', data_entrega_prevista: '', observacoes: '' }}
        />
      )}

      {tab === 'itens' && (
        <ResourceCrud
          resource="vendas/itens-pedido"
          title="Itens de Pedido"
          createLabel="+ Novo Item"
          emptyIcon="📦"
          emptyText="Nenhum item encontrado."
          titleField="descricao"
          columns={[
            { key: 'descricao', label: 'Descrição' },
            { key: 'quantidade', label: 'Qtd' },
            { key: 'valor_unitario', label: 'Valor Unit.', money: true },
            { key: 'valor_total', label: 'Total', money: true },
          ]}
          fields={[
            { name: 'pedido', label: 'Pedido', type: 'select-remote', endpoint: 'vendas/pedidos', labelField: 'numero' },
            { name: 'descricao', label: 'Descrição', type: 'text' },
            { name: 'quantidade', label: 'Quantidade', type: 'number', min: '1' },
            { name: 'valor_unitario', label: 'Valor Unitário (R$)', type: 'number', step: '0.01', min: '0' },
          ]}
          emptyForm={{ pedido: '', descricao: '', quantidade: 1, valor_unitario: '' }}
        />
      )}
    </div>
  )
}

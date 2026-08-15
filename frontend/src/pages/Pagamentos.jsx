import { useState } from 'react'
import ResourceCrud from '../components/ui/ResourceCrud.jsx'

const TABS = [
  { key: 'cobrancas', label: 'Cobranças' },
  { key: 'parcelas', label: 'Parcelas' },
  { key: 'metodos', label: 'Métodos' },
]

const STATUS_COBRANCA = [
  { value: 'PENDENTE', label: 'Pendente' },
  { value: 'PAGO', label: 'Pago' },
  { value: 'CANCELADO', label: 'Cancelado' },
  { value: 'ATRASADO', label: 'Atrasado' },
]

const STATUS_PARCELA = [
  { value: 'PENDENTE', label: 'Pendente' },
  { value: 'PAGO', label: 'Pago' },
  { value: 'CANCELADO', label: 'Cancelado' },
]

const NOME_METODO = [
  { value: 'PIX', label: 'PIX' },
  { value: 'BOLETO', label: 'Boleto' },
  { value: 'CARTAO_CREDITO', label: 'Cartão de Crédito' },
  { value: 'CARTAO_DEBITO', label: 'Cartão de Débito' },
  { value: 'DINHEIRO', label: 'Dinheiro' },
  { value: 'OUTRO', label: 'Outro' },
]

export default function Pagamentos() {
  const [tab, setTab] = useState('cobrancas')

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Pagamentos</h1>
        <p className="text-sm text-gray-500 mt-0.5 dark:text-slate-400">Recebimento de clientes: PIX, boleto, cartão</p>
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

      {tab === 'cobrancas' && (
        <ResourceCrud
          resource="pagamentos/cobrancas"
          title="Cobranças"
          createLabel="+ Nova Cobrança"
          emptyIcon="💳"
          emptyText="Nenhuma cobrança encontrada."
          titleField="descricao"
          columns={[
            { key: 'cliente_nome', label: 'Cliente' },
            { key: 'descricao', label: 'Descrição' },
            { key: 'valor', label: 'Valor', money: true },
            { key: 'vencimento', label: 'Vencimento', date: true },
            { key: 'status_label', label: 'Status', badge: true },
            { key: 'metodo_nome', label: 'Método' },
          ]}
          fields={[
            { name: 'cliente', label: 'Cliente', type: 'select-remote', endpoint: 'clientes', labelField: 'nome_razao_social' },
            { name: 'descricao', label: 'Descrição', type: 'text' },
            { name: 'valor', label: 'Valor (R$)', type: 'number', step: '0.01', min: '0' },
            { name: 'vencimento', label: 'Vencimento', type: 'date' },
            { name: 'status', label: 'Status', type: 'select', options: STATUS_COBRANCA },
            { name: 'metodo', label: 'Método', type: 'select-remote', endpoint: 'pagamentos/metodos', labelField: 'nome_display' },
            { name: 'data_pagamento', label: 'Data Pagamento', type: 'date' },
            { name: 'observacoes', label: 'Observações', type: 'textarea' },
          ]}
          emptyForm={{ cliente: '', descricao: '', valor: '', vencimento: '', status: 'PENDENTE', metodo: '', data_pagamento: '', observacoes: '' }}
        />
      )}

      {tab === 'parcelas' && (
        <ResourceCrud
          resource="pagamentos/parcelas"
          title="Parcelas"
          createLabel="+ Nova Parcela"
          emptyIcon="🔢"
          emptyText="Nenhuma parcela encontrada."
          titleField="numero"
          columns={[
            { key: 'numero', label: 'Nº' },
            { key: 'valor', label: 'Valor', money: true },
            { key: 'vencimento', label: 'Vencimento', date: true },
            { key: 'status_label', label: 'Status', badge: true },
          ]}
          fields={[
            { name: 'cobranca', label: 'Cobrança', type: 'select-remote', endpoint: 'pagamentos/cobrancas', labelField: 'descricao' },
            { name: 'numero', label: 'Número', type: 'number', min: '1' },
            { name: 'valor', label: 'Valor (R$)', type: 'number', step: '0.01', min: '0' },
            { name: 'vencimento', label: 'Vencimento', type: 'date' },
            { name: 'status', label: 'Status', type: 'select', options: STATUS_PARCELA },
            { name: 'data_pagamento', label: 'Data Pagamento', type: 'date' },
          ]}
          emptyForm={{ cobranca: '', numero: '', valor: '', vencimento: '', status: 'PENDENTE', data_pagamento: '' }}
        />
      )}

      {tab === 'metodos' && (
        <ResourceCrud
          resource="pagamentos/metodos"
          title="Métodos de Pagamento"
          createLabel="+ Novo Método"
          emptyIcon="⚙️"
          emptyText="Nenhum método cadastrado."
          titleField="nome_display"
          columns={[
            { key: 'nome_display', label: 'Nome' },
            { key: 'ativo', label: 'Ativo', boolean: true },
          ]}
          fields={[
            { name: 'nome', label: 'Nome', type: 'select', options: NOME_METODO },
            { name: 'ativo', label: 'Ativo', type: 'checkbox' },
          ]}
          emptyForm={{ nome: 'PIX', ativo: true }}
        />
      )}
    </div>
  )
}

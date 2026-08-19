import { useState } from 'react'
import ResourceCrud from '../components/ui/ResourceCrud.jsx'

const TABS = [
  { key: 'colaboradores', label: 'Colaboradores' },
  { key: 'cargos', label: 'Cargos' },
  { key: 'folhas', label: 'Folha de Pagamento' },
  { key: 'ferias', label: 'Férias' },
]

const REGIME = [
  { value: 'CLT', label: 'CLT' },
  { value: 'PJ', label: 'PJ' },
  { value: 'ESTAGIO', label: 'Estágio' },
  { value: 'SOCIO', label: 'Sócio' },
]

const STATUS_FOLHA = [
  { value: 'ABERTA', label: 'Aberta' },
  { value: 'FECHADA', label: 'Fechada' },
  { value: 'PAGA', label: 'Paga' },
]

const STATUS_FERIAS = [
  { value: 'AGENDADO', label: 'Agendado' },
  { value: 'EM_ANDAMENTO', label: 'Em Andamento' },
  { value: 'CONCLUIDO', label: 'Concluído' },
]

export default function Rh() {
  const [tab, setTab] = useState('colaboradores')

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Recursos Humanos</h1>
        <p className="text-sm text-gray-500 mt-0.5 dark:text-slate-400">Cadastro, folha de pagamento, férias, admissão/demissão</p>
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

      {tab === 'colaboradores' && (
        <ResourceCrud
          resource="rh/colaboradores"
          title="Colaboradores"
          createLabel="+ Novo Colaborador"
          emptyIcon="👔"
          emptyText="Nenhum colaborador encontrado."
          titleField="nome"
          columns={[
            { key: 'nome', label: 'Nome' },
            { key: 'cargo_nome', label: 'Cargo' },
            { key: 'regime_label', label: 'Regime', badge: true },
            { key: 'salario_atual', label: 'Salário', money: true },
            { key: 'data_admissao', label: 'Admissão', date: true },
            { key: 'tem_acesso', label: 'Acesso', boolean: true },
            { key: 'usuario_email', label: 'E-mail de Acesso' },
          ]}
          fields={[
            { name: 'nome', label: 'Nome', type: 'text' },
            { name: 'cpf', label: 'CPF', type: 'text', placeholder: 'somente números' },
            { name: 'email', label: 'E-mail', type: 'email' },
            { name: 'cargo', label: 'Cargo', type: 'select-remote', endpoint: 'rh/cargos', labelField: 'nome' },
            { name: 'regime', label: 'Regime', type: 'select', options: REGIME },
            { name: 'salario_atual', label: 'Salário Atual (R$)', type: 'number', step: '0.01', min: '0' },
            { name: 'data_admissao', label: 'Data de Admissão', type: 'date' },
            { name: 'data_demissao', label: 'Data de Demissão', type: 'date' },
            { name: 'observacoes', label: 'Observações', type: 'textarea' },
            { name: 'acesso_divider', type: 'divider', hideOnEdit: true },
            {
              name: 'criar_usuario',
              label: 'Criar acesso ao sistema',
              type: 'checkbox',
              colSpan2: true,
              hideOnEdit: true,
              onToggle: (checked, next) => (checked && !next.usuario_email ? { ...next, usuario_email: next.email } : next),
            },
            {
              name: 'usuario_email',
              label: 'E-mail de acesso',
              type: 'email',
              colSpan2: true,
              hideOnEdit: true,
              showIf: (form) => !!form.criar_usuario,
            },
            {
              name: 'usuario_senha',
              label: 'Senha (opcional)',
              type: 'password',
              colSpan2: true,
              hideOnEdit: true,
              showIf: (form) => !!form.criar_usuario,
              helpText: 'Deixe em branco para enviar link de definição de senha por e-mail.',
            },
          ]}
          emptyForm={{
            nome: '', cpf: '', email: '', cargo: '', regime: 'CLT', salario_atual: '', data_admissao: '', data_demissao: '', observacoes: '',
            criar_usuario: false, usuario_email: '', usuario_senha: '',
          }}
          onBeforeSubmit={(form, editingId) => {
            if (!editingId && form.criar_usuario && !form.usuario_email) {
              return 'Informe o e-mail de acesso para criar o usuário.'
            }
            return true
          }}
        />
      )}

      {tab === 'cargos' && (
        <ResourceCrud
          resource="rh/cargos"
          title="Cargos"
          createLabel="+ Novo Cargo"
          emptyIcon="🏷️"
          emptyText="Nenhum cargo cadastrado."
          titleField="nome"
          columns={[
            { key: 'nome', label: 'Nome' },
            { key: 'salario_base', label: 'Salário Base', money: true },
          ]}
          fields={[
            { name: 'nome', label: 'Nome', type: 'text' },
            { name: 'salario_base', label: 'Salário Base (R$)', type: 'number', step: '0.01', min: '0' },
            { name: 'descricao', label: 'Descrição', type: 'textarea' },
          ]}
          emptyForm={{ nome: '', salario_base: '', descricao: '' }}
        />
      )}

      {tab === 'folhas' && (
        <ResourceCrud
          resource="rh/folhas"
          title="Folha de Pagamento"
          createLabel="+ Nova Folha"
          emptyIcon="🧾"
          emptyText="Nenhuma folha encontrada."
          titleField="colaborador_nome"
          columns={[
            { key: 'colaborador_nome', label: 'Colaborador' },
            { key: 'mes_referencia', label: 'Mês', date: true },
            { key: 'salario_bruto', label: 'Bruto', money: true },
            { key: 'salario_liquido', label: 'Líquido', money: true },
            { key: 'status_label', label: 'Status', badge: true },
          ]}
          fields={[
            { name: 'colaborador', label: 'Colaborador', type: 'select-remote', endpoint: 'rh/colaboradores', labelField: 'nome' },
            { name: 'mes_referencia', label: 'Mês de Referência', type: 'date' },
            { name: 'salario_bruto', label: 'Salário Bruto (R$)', type: 'number', step: '0.01', min: '0' },
            { name: 'descontos', label: 'Descontos (R$)', type: 'number', step: '0.01', min: '0' },
            { name: 'status', label: 'Status', type: 'select', options: STATUS_FOLHA },
            { name: 'observacoes', label: 'Observações', type: 'textarea' },
          ]}
          emptyForm={{ colaborador: '', mes_referencia: '', salario_bruto: '', descontos: '0', status: 'ABERTA', observacoes: '' }}
        />
      )}

      {tab === 'ferias' && (
        <ResourceCrud
          resource="rh/ferias"
          title="Férias"
          createLabel="+ Novo Registro"
          emptyIcon="🏖️"
          emptyText="Nenhum registro de férias encontrado."
          titleField="colaborador_nome"
          columns={[
            { key: 'colaborador_nome', label: 'Colaborador' },
            { key: 'data_inicio', label: 'Início', date: true },
            { key: 'data_fim', label: 'Fim', date: true },
            { key: 'dias', label: 'Dias' },
            { key: 'status_label', label: 'Status', badge: true },
          ]}
          fields={[
            { name: 'colaborador', label: 'Colaborador', type: 'select-remote', endpoint: 'rh/colaboradores', labelField: 'nome' },
            { name: 'data_inicio', label: 'Data de Início', type: 'date' },
            { name: 'data_fim', label: 'Data de Fim', type: 'date' },
            { name: 'status', label: 'Status', type: 'select', options: STATUS_FERIAS },
          ]}
          emptyForm={{ colaborador: '', data_inicio: '', data_fim: '', status: 'AGENDADO' }}
        />
      )}
    </div>
  )
}

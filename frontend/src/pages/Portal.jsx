import ResourceCrud from '../components/ui/ResourceCrud.jsx'

export default function Portal() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Portal do Cliente</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Acessos de clientes ao portal — perfil separado do admin/operacional
        </p>
      </div>

      <ResourceCrud
        resource="portal/acessos"
        title="Acessos do Portal"
        createLabel="+ Novo Acesso"
        emptyIcon="🌐"
        emptyText="Nenhum acesso cadastrado."
        titleField="cliente_nome"
        columns={[
          { key: 'usuario_email', label: 'Usuário' },
          { key: 'cliente_nome', label: 'Cliente' },
          { key: 'ativo', label: 'Ativo', boolean: true },
          { key: 'ultimo_acesso', label: 'Último acesso', datetime: true },
        ]}
        fields={[
          {
            name: 'usuario', label: 'ID do Usuário', type: 'number', min: '1',
            placeholder: 'ID do usuário já cadastrado (accounts.User)',
          },
          { name: 'cliente', label: 'Cliente', type: 'select-remote', endpoint: 'clientes', labelField: 'nome_razao_social' },
          { name: 'ativo', label: 'Ativo', type: 'checkbox' },
        ]}
        emptyForm={{ usuario: '', cliente: '', ativo: true }}
      />
    </div>
  )
}

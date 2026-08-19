import { Mail } from 'lucide-react'
import ResourceCrud from '../components/ui/ResourceCrud.jsx'
import api from '../api/client.js'
import useAuthStore from '../stores/authStore.js'

export default function Usuarios() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Usuários</h1>
        <p className="text-sm text-gray-500 mt-0.5 dark:text-slate-400">Gerencie os acessos administrativos ao sistema</p>
      </div>

      <ResourceCrud
        resource="accounts/usuarios"
        title="Usuários"
        createLabel="+ Novo Usuário"
        emptyIcon="👤"
        emptyText="Nenhum usuário cadastrado."
        titleField="nome_completo"
        columns={[
          { key: 'nome_completo', label: 'Nome' },
          { key: 'email', label: 'E-mail' },
          { key: 'colaborador_nome', label: 'Colaborador' },
          { key: 'is_staff', label: 'Admin', boolean: true },
          { key: 'is_active', label: 'Ativo', boolean: true },
          { key: 'date_joined', label: 'Desde', date: true },
        ]}
        fields={[
          { name: 'email', label: 'E-mail', type: 'email', required: true },
          { name: 'nome_completo', label: 'Nome completo', type: 'text', required: true },
          { name: 'telefone', label: 'Telefone', type: 'text' },
          {
            name: 'password',
            label: 'Senha',
            type: 'password',
            helpText: (isEditing) =>
              isEditing
                ? 'Deixe em branco para não alterar a senha atual.'
                : 'Deixe em branco para enviar link de definição de senha por e-mail.',
          },
          { name: 'is_staff', label: 'Administrador', type: 'checkbox' },
        ]}
        emptyForm={{ email: '', nome_completo: '', telefone: '', password: '', is_staff: false }}
        deleteLabel="Desativar"
        deleteConfirm={(item) =>
          `Desativar o acesso de "${item.nome_completo}"? O usuário não poderá mais fazer login, mas o registro não será apagado.`
        }
        rowActions={[
          {
            label: 'Reenviar acesso',
            icon: Mail,
            variant: 'secondary',
            showIf: (item) => item.is_active,
            refresh: false,
            successMessage: 'Link de acesso reenviado.',
            errorMessage: 'Erro ao reenviar acesso.',
            onClick: (item) => api.post('/accounts/solicitar-acesso/', { usuario_id: item.id }),
          },
        ]}
        onBeforeSubmit={(form, editingId) => {
          const currentUser = useAuthStore.getState().user
          const isSelf = editingId && currentUser && String(editingId) === String(currentUser.id)
          if (isSelf && !form.is_staff) {
            const confirmado = window.confirm(
              'Você está removendo seu próprio acesso de administrador. Depois de salvar, não poderá mais acessar esta tela. Deseja continuar?',
            )
            if (!confirmado) return false
          }
          return true
        }}
      />
    </div>
  )
}

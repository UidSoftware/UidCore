import { useAuth } from '../hooks/useAuth.js'
import Card from '../components/ui/Card.jsx'

const metrics = [
  {
    label: 'Receitas do Mês',
    value: 'R$ —',
    sub: 'Nenhum dado disponível',
    icon: '📈',
    color: 'text-accent-600 bg-accent-50',
  },
  {
    label: 'Despesas do Mês',
    value: 'R$ —',
    sub: 'Nenhum dado disponível',
    icon: '📉',
    color: 'text-red-600 bg-red-50',
  },
  {
    label: 'Saldo Atual',
    value: 'R$ —',
    sub: 'Nenhum dado disponível',
    icon: '💰',
    color: 'text-primary-600 bg-primary-50',
  },
  {
    label: 'Agendamentos Hoje',
    value: '—',
    sub: 'Nenhum dado disponível',
    icon: '📅',
    color: 'text-purple-600 bg-purple-50',
  },
]

export default function Dashboard() {
  const { user } = useAuth()
  const firstName = user?.nome_completo?.split(' ')[0] || user?.email || 'Usuário'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Bem-vindo ao UidCore, {firstName}!
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Visão geral do seu negócio — tudo em um lugar.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {metrics.map(({ label, value, sub, icon, color }) => (
          <Card key={label}>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
                <p className="mt-1 text-xs text-gray-400">{sub}</p>
              </div>
              <div className={`p-2.5 rounded-xl ${color}`}>
                <span className="text-xl leading-none">{icon}</span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="Atividade Recente">
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <span className="text-4xl mb-2">📋</span>
            <p className="text-sm text-gray-500">Nenhuma atividade registrada ainda.</p>
          </div>
        </Card>
        <Card title="Próximos Agendamentos">
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <span className="text-4xl mb-2">📆</span>
            <p className="text-sm text-gray-500">Nenhum agendamento para hoje.</p>
          </div>
        </Card>
      </div>
    </div>
  )
}

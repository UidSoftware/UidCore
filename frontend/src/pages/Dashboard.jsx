import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth.js'
import Card from '../components/ui/Card.jsx'
import client from '../api/client.js'

function formatCurrency(value) {
  return parseFloat(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

export default function Dashboard() {
  const { user } = useAuth()
  const firstName = user?.nome_completo?.split(' ')[0] || user?.email || 'Usuário'

  const [dados, setDados] = useState(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState(null)

  useEffect(() => {
    carregarDashboard()
  }, [])

  const carregarDashboard = async () => {
    try {
      setLoading(true)
      setErro(null)
      const { data } = await client.get('/financeiro/dashboard/')
      setDados(data)
    } catch {
      setErro('Não foi possível carregar o painel. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">
            Bem-vindo ao UidCore, {firstName}!
          </h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            Visão geral do seu negócio — tudo em um lugar.
          </p>
        </div>
        <div className="text-center py-12 text-gray-400 dark:text-slate-500 text-sm">Carregando...</div>
      </div>
    )
  }

  if (erro) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">
            Bem-vindo ao UidCore, {firstName}!
          </h1>
        </div>
        <div className="text-center py-12 text-red-600 dark:text-red-400 text-sm">{erro}</div>
      </div>
    )
  }

  const cards = [
    {
      label: 'Receitas do Mês',
      value: formatCurrency(dados.receita_mes || '0'),
      color: 'text-accent-600 bg-accent-50 dark:bg-emerald-950/40 dark:text-emerald-300',
      icon: '📈',
    },
    {
      label: 'Despesas do Mês',
      value: formatCurrency(dados.despesa_mes || '0'),
      color: 'text-red-600 bg-red-50 dark:bg-red-950/40 dark:text-red-300',
      icon: '📉',
    },
    {
      label: 'Saldo Atual',
      value: formatCurrency(dados.saldo_total_contas || '0'),
      color: 'text-primary-600 bg-primary-50 dark:bg-violet-950/40 dark:text-violet-300',
      icon: '💰',
    },
    {
      label: 'MRR',
      value: formatCurrency(dados.mrr || '0'),
      color: 'text-purple-600 bg-purple-50 dark:bg-violet-950/40 dark:text-violet-300',
      icon: '📊',
    },
  ]

  const receitas_atrasadas = dados.receitas_atrasadas || 0
  const despesas_atrasadas = dados.despesas_atrasadas || 0
  const receitas_vencer = dados.receitas_vencer || []
  const despesas_vencer = dados.despesas_vencer || []
  const grafico = dados.grafico_6_meses || []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">
          Bem-vindo ao UidCore, {firstName}!
        </h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
          Visão geral do seu negócio — tudo em um lugar.
        </p>
      </div>

      {/* Alertas de atrasados */}
      {(receitas_atrasadas > 0 || despesas_atrasadas > 0) && (
        <div className="flex flex-wrap gap-2">
          {receitas_atrasadas > 0 && (
            <span className="px-3 py-1.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">
              {receitas_atrasadas} receita{receitas_atrasadas > 1 ? 's' : ''} atrasada{receitas_atrasadas > 1 ? 's' : ''}
            </span>
          )}
          {despesas_atrasadas > 0 && (
            <span className="px-3 py-1.5 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800 dark:bg-amber-900/30 dark:text-amber-300">
              {despesas_atrasadas} despesa{despesas_atrasadas > 1 ? 's' : ''} atrasada{despesas_atrasadas > 1 ? 's' : ''}
            </span>
          )}
        </div>
      )}

      {/* 4 cards principais */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {cards.map(({ label, value, color, icon }) => (
          <Card key={label}>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide">{label}</p>
                <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-slate-100">{value}</p>
              </div>
              <div className={`p-2.5 rounded-xl ${color}`}>
                <span className="text-xl leading-none">{icon}</span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Listas de vencimentos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="Receitas a Vencer (30 dias)">
          {receitas_vencer.length === 0 ? (
            <div className="text-center py-8 text-gray-400 dark:text-slate-500">
              <p className="text-sm">Nenhum item nos próximos 30 dias.</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100 dark:divide-navy-700">
              {receitas_vencer.map((item) => (
                <li key={item.id} className="py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-slate-100 truncate">{item.descricao}</p>
                    <p className="text-xs text-gray-400 dark:text-slate-500">
                      {item.cliente__nome_razao_social || '—'} · vence {item.vencimento}
                    </p>
                  </div>
                  <span className="text-sm font-semibold text-accent-600 dark:text-emerald-400 shrink-0">
                    {formatCurrency(item.valor_liquido)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Despesas a Vencer (30 dias)">
          {despesas_vencer.length === 0 ? (
            <div className="text-center py-8 text-gray-400 dark:text-slate-500">
              <p className="text-sm">Nenhum item nos próximos 30 dias.</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100 dark:divide-navy-700">
              {despesas_vencer.map((item) => (
                <li key={item.id} className="py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-slate-100 truncate">{item.descricao}</p>
                    <p className="text-xs text-gray-400 dark:text-slate-500">
                      {item.fornecedor || '—'} · vence {item.vencimento}
                    </p>
                  </div>
                  <span className="text-sm font-semibold text-red-600 dark:text-red-400 shrink-0">
                    {formatCurrency(item.valor_liquido)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {/* Resultado dos últimos 6 meses */}
      <Card title="Resultado dos Últimos 6 Meses">
        {grafico.length === 0 ? (
          <div className="text-center py-8 text-gray-400 dark:text-slate-500">
            <p className="text-sm">Nenhum dado disponível.</p>
          </div>
        ) : (
          <div className="overflow-x-auto -mx-6 -my-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-100 text-left dark:bg-navy-900">
                  <th className="px-6 py-3 font-semibold text-gray-700 dark:text-slate-400">Mês</th>
                  <th className="px-4 py-3 font-semibold text-gray-700 text-right dark:text-slate-400">Receita</th>
                  <th className="px-4 py-3 font-semibold text-gray-700 text-right dark:text-slate-400">Despesa</th>
                  <th className="px-6 py-3 font-semibold text-gray-700 text-right dark:text-slate-400">Resultado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-navy-700">
                {grafico.map((row) => {
                  const resultado = parseFloat(row.resultado || '0')
                  return (
                    <tr key={row.mes} className="hover:bg-gray-50 dark:hover:bg-navy-700/60">
                      <td className="px-6 py-3 font-medium text-gray-900 dark:text-slate-100">{row.label}</td>
                      <td className="px-4 py-3 text-right text-accent-600 dark:text-emerald-400">{formatCurrency(row.receita)}</td>
                      <td className="px-4 py-3 text-right text-red-600 dark:text-red-400">{formatCurrency(row.despesa)}</td>
                      <td className={`px-6 py-3 text-right font-semibold ${resultado >= 0 ? 'text-green-700 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                        {formatCurrency(row.resultado)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}

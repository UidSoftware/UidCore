import { AlertTriangle, CheckCircle } from 'lucide-react'

const BRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

function KpiCard({ label, value, color = 'blue' }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300',
    green: 'bg-green-50 text-green-700 dark:bg-emerald-950/40 dark:text-emerald-300',
    red: 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300',
    yellow: 'bg-yellow-50 text-yellow-700 dark:bg-amber-950/40 dark:text-amber-300',
  }
  return (
    <div className={`rounded-xl p-4 ${colors[color]}`}>
      <p className="text-xs font-medium opacity-70">{label}</p>
      <p className="text-lg font-bold mt-1 font-mono">{value}</p>
    </div>
  )
}

/**
 * Resumo de uma sessão de caixa — compartilhado entre
 * FechamentoCaixa.jsx e RelatorioSessoes.jsx (modal de detalhe).
 *
 * Props:
 *   sessao  — objeto sessão completo vindo da API
 *   resumo  — { por_metodo: [{metodo_nome, total}], vendas_dinheiro, sangrias, suprimentos }
 */
export default function ResumoSessao({ sessao, resumo = {} }) {
  if (!sessao) return null

  const {
    valor_abertura = 0,
    valor_fechamento_calculado,
    valor_fechamento_informado,
    diferenca,
    status,
  } = sessao

  const totalSangrias = resumo.sangrias || 0
  const totalSuprimentos = resumo.suprimentos || 0
  const totalVendas = (resumo.por_metodo || []).reduce((acc, m) => acc + parseFloat(m.total || 0), 0)

  const diffNum = parseFloat(diferenca || 0)
  const temDiferenca = Math.abs(diffNum) >= 0.01

  return (
    <div className="space-y-4">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Abertura" value={BRL(valor_abertura)} color="blue" />
        <KpiCard label="Total Vendas" value={BRL(totalVendas)} color="green" />
        <KpiCard label="Sangrias" value={`- ${BRL(totalSangrias)}`} color="red" />
        <KpiCard label="Suprimentos" value={`+ ${BRL(totalSuprimentos)}`} color="green" />
      </div>

      {/* Vendas por forma de pagamento */}
      {(resumo.por_metodo || []).length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm dark:bg-navy-800 dark:border-navy-600 dark:shadow-none">
          <div className="px-4 py-3 border-b border-gray-100 dark:border-navy-700">
            <p className="text-sm font-semibold text-gray-700 dark:text-slate-200">Vendas por forma de pagamento</p>
          </div>
          <div className="px-4 py-3 space-y-2">
            {resumo.por_metodo.map((m, i) => (
              <div key={i} className="flex justify-between items-center text-sm">
                <span className="text-gray-600 dark:text-slate-400">{m.metodo_nome}</span>
                <span className="font-mono font-medium text-gray-900 dark:text-slate-100">{BRL(m.total)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Valor calculado e fechamento */}
      {status === 'FECHADA' && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm px-4 py-4 space-y-3 dark:bg-navy-800 dark:border-navy-600 dark:shadow-none">
          {valor_fechamento_calculado != null && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-slate-400">Valor calculado em caixa</span>
              <span className="font-mono font-medium text-gray-900 text-lg dark:text-slate-100">{BRL(valor_fechamento_calculado)}</span>
            </div>
          )}
          {valor_fechamento_informado != null && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-slate-400">Contagem física</span>
              <span className="font-mono font-medium text-gray-900 dark:text-slate-100">{BRL(valor_fechamento_informado)}</span>
            </div>
          )}
          {diferenca != null && (
            <div className={`flex justify-between items-center pt-2 border-t border-gray-100 dark:border-navy-700 ${temDiferenca ? 'text-red-700 dark:text-red-400' : 'text-green-700 dark:text-emerald-400'}`}>
              <span className="text-sm font-medium flex items-center gap-1">
                {temDiferenca ? <AlertTriangle size={14} /> : <CheckCircle size={14} />}
                Diferença
              </span>
              <span className="font-mono font-bold">{BRL(diferenca)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

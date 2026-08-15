import { Banknote, Zap, CreditCard, FileText, MoreHorizontal, X, Plus } from 'lucide-react'

const BRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

// Mapeia nome do método para ícone e cor
function MetodoIcon({ nome }) {
  const n = (nome || '').toUpperCase()
  if (n.includes('DINHEIRO') || n.includes('ESPECIE')) return <Banknote size={18} className="text-green-700" />
  if (n.includes('PIX')) return <Zap size={18} className="text-green-600" />
  if (n.includes('CREDITO') || n.includes('CRÉDITO')) return <CreditCard size={18} className="text-purple-600" />
  if (n.includes('DEBITO') || n.includes('DÉBITO')) return <CreditCard size={18} className="text-blue-600" />
  if (n.includes('BOLETO')) return <FileText size={18} className="text-blue-600" />
  return <MoreHorizontal size={18} className="text-gray-500 dark:text-slate-400" />
}

/**
 * Componente de split de pagamento (RF-09).
 *
 * Props:
 *   metodos       — lista de MetodoPagamento [{id, nome, conta_padrao, taxa_percentual_padrao}]
 *   contas        — lista de Conta [{id, nome, tipo}]
 *   total         — Decimal (valor total da venda)
 *   linhas        — estado atual do split: [{metodo_id, metodo_nome, valor, conta, taxa_percentual, prazo_dias}]
 *   onChange(linhas) — callback quando o split muda
 */
export default function SplitPagamento({ metodos = [], contas = [], total = 0, linhas = [], onChange }) {
  const somaLinhas = linhas.reduce((acc, l) => acc + parseFloat(l.valor || 0), 0)
  const falta = parseFloat(total) - somaLinhas
  const eExato = Math.abs(falta) < 0.01

  const adicionarMetodo = (metodo) => {
    // Evita duplicar o mesmo método? Não — pode haver 2 cartões. Permite adicionar sempre.
    const novaLinha = {
      _key: Date.now(),
      metodo_id: metodo.id,
      metodo_nome: metodo.nome,
      metodo_cartao_credito: (metodo.nome || '').toUpperCase().includes('CREDITO') ||
                              (metodo.nome || '').toUpperCase().includes('CRÉDITO'),
      conta: metodo.conta_padrao || '',
      valor: linhas.length === 0 ? String(parseFloat(total).toFixed(2)) : '',
      taxa_percentual: metodo.taxa_percentual_padrao || '',
      prazo_dias: '',
    }
    onChange([...linhas, novaLinha])
  }

  const removerLinha = (key) => {
    onChange(linhas.filter((l) => l._key !== key))
  }

  const atualizarLinha = (key, campo, valor) => {
    onChange(linhas.map((l) => l._key === key ? { ...l, [campo]: valor } : l))
  }

  return (
    <div className="space-y-4">
      {/* Grid de chips de métodos disponíveis */}
      <div>
        <p className="text-xs font-medium text-gray-500 mb-2 dark:text-slate-400">Adicionar forma de pagamento</p>
        <div className="grid grid-cols-2 gap-2">
          {metodos.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => adicionarMetodo(m)}
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-sm font-medium text-gray-700 transition-colors text-left dark:border-navy-600 dark:bg-navy-800 dark:hover:bg-navy-700 dark:text-slate-200"
            >
              <MetodoIcon nome={m.nome} />
              <span className="truncate">{m.nome}</span>
              <Plus size={12} className="ml-auto text-primary-600 shrink-0 dark:text-violet-400" />
            </button>
          ))}
        </div>
      </div>

      {/* Linhas de pagamento selecionadas */}
      {linhas.length > 0 && (
        <div className="space-y-3">
          {linhas.map((linha) => (
            <div key={linha._key} className="rounded-lg border border-gray-200 p-4 space-y-3 bg-gray-50 dark:border-navy-600 dark:bg-navy-900/50">
              <div className="flex items-center gap-2">
                <MetodoIcon nome={linha.metodo_nome} />
                <span className="text-sm font-medium text-gray-800 flex-1 dark:text-slate-200">{linha.metodo_nome}</span>
                <button
                  type="button"
                  onClick={() => removerLinha(linha._key)}
                  className="p-1 text-gray-400 hover:text-red-600 transition-colors rounded dark:text-slate-500 dark:hover:text-red-400"
                >
                  <X size={14} />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {/* Valor */}
                <div>
                  <label className="block text-sm text-gray-500 mb-1 dark:text-slate-400">Valor (R$)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={linha.valor}
                    onChange={(e) => atualizarLinha(linha._key, 'valor', e.target.value)}
                    placeholder="0,00"
                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-right font-mono focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:focus:ring-violet-500"
                  />
                </div>

                {/* Conta (se não há conta_padrao) */}
                <div>
                  <label className="block text-sm text-gray-500 mb-1 dark:text-slate-400">Conta de destino</label>
                  <select
                    value={linha.conta}
                    onChange={(e) => atualizarLinha(linha._key, 'conta', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:focus:ring-violet-500"
                  >
                    <option value="">Selecione...</option>
                    {contas.map((c) => (
                      <option key={c.id} value={c.id}>{c.nome}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Campos extras para cartão de crédito */}
              {linha.metodo_cartao_credito && (
                <div className="grid grid-cols-2 gap-3 pt-2 border-t border-gray-200 dark:border-navy-700">
                  <div>
                    <label className="block text-sm text-gray-500 mb-1 dark:text-slate-400">Taxa (%)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      value={linha.taxa_percentual}
                      onChange={(e) => atualizarLinha(linha._key, 'taxa_percentual', e.target.value)}
                      placeholder="Ex: 2,99"
                      className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:focus:ring-violet-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-500 mb-1 dark:text-slate-400">Prazo (dias)</label>
                    <input
                      type="number"
                      step="1"
                      min="0"
                      value={linha.prazo_dias}
                      onChange={(e) => atualizarLinha(linha._key, 'prazo_dias', e.target.value)}
                      placeholder="Ex: 30"
                      className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:focus:ring-violet-500"
                    />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Resumo do split */}
      {linhas.length > 0 && (
        <div className="flex justify-between items-center text-sm pt-1">
          <span className="text-gray-600 dark:text-slate-400">
            Alocado: <span className="font-mono font-medium">{BRL(somaLinhas)}</span>
          </span>
          {!eExato && (
            <span className={`font-medium ${falta > 0 ? 'text-yellow-700 dark:text-amber-400' : 'text-green-700 dark:text-emerald-400'}`}>
              {falta > 0 ? `Falta alocar: ${BRL(falta)}` : `Troco: ${BRL(Math.abs(falta))}`}
            </span>
          )}
          {eExato && (
            <span className="text-green-700 font-medium dark:text-emerald-400">Pagamento completo</span>
          )}
        </div>
      )}
    </div>
  )
}

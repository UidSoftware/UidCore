import { Trash2, Plus, Minus } from 'lucide-react'

const BRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

/**
 * Item do carrinho de venda.
 * Props:
 *   item: { id, produto_nome, produto_unidade, quantidade, valor_unitario,
 *            desconto_item, valor_total }
 *   onQuantidade(itemId, novaQtd)  — novaQtd = 0 remove o item
 *   onRemover(itemId)
 *   disabled — bloqueia edição (venda finalizada/cancelada)
 */
export default function CarrinhoItem({ item, onQuantidade, onRemover, disabled = false }) {
  const handleMinus = () => {
    const nova = parseFloat(item.quantidade) - 1
    if (nova <= 0) {
      onRemover(item.id)
    } else {
      onQuantidade(item.id, nova)
    }
  }

  const handlePlus = () => {
    onQuantidade(item.id, parseFloat(item.quantidade) + 1)
  }

  const handleInput = (e) => {
    const val = parseFloat(e.target.value)
    if (!isNaN(val) && val > 0) {
      onQuantidade(item.id, val)
    }
  }

  return (
    <div className="border-b border-gray-100 last:border-0 py-3 dark:border-navy-700">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate dark:text-slate-100">{item.produto_nome}</p>
          <p className="text-xs text-gray-500 mt-0.5 dark:text-slate-400">
            {BRL(item.valor_unitario)} / {item.produto_unidade || 'UN'}
          </p>
          {parseFloat(item.desconto_item || 0) > 0 && (
            <p className="text-xs text-gray-400 mt-0.5 dark:text-slate-500">
              - {BRL(item.desconto_item)} desconto
            </p>
          )}
        </div>

        <div className="flex items-center gap-1">
          <p className="text-sm font-medium text-gray-900 font-mono whitespace-nowrap dark:text-slate-100">
            {BRL(item.valor_total)}
          </p>
          {!disabled && (
            <button
              type="button"
              onClick={() => onRemover(item.id)}
              className="ml-2 p-1 text-gray-400 hover:text-red-600 transition-colors rounded dark:text-slate-500 dark:hover:text-red-400"
              title="Remover item"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>

      {!disabled && (
        <div className="flex items-center gap-2 mt-2">
          <button
            type="button"
            onClick={handleMinus}
            className="w-6 h-6 flex items-center justify-center rounded-full border border-gray-300 text-gray-600 hover:bg-gray-100 transition-colors shrink-0 dark:border-navy-500 dark:text-slate-300 dark:hover:bg-navy-700"
            title="Diminuir quantidade"
          >
            <Minus size={12} />
          </button>
          <input
            type="number"
            value={item.quantidade}
            onChange={handleInput}
            step="1"
            min="0.001"
            className="w-14 text-center text-sm border border-gray-300 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:focus:ring-violet-500"
          />
          <button
            type="button"
            onClick={handlePlus}
            className="w-6 h-6 flex items-center justify-center rounded-full border border-gray-300 bg-primary-50 text-primary-600 hover:bg-primary-100 transition-colors shrink-0 dark:border-navy-500 dark:bg-violet-900/30 dark:text-violet-300 dark:hover:bg-violet-900/50"
            title="Aumentar quantidade"
          >
            <Plus size={12} />
          </button>
          <span className="text-xs text-gray-400 ml-1 dark:text-slate-500">{item.produto_unidade || 'UN'}</span>
        </div>
      )}
    </div>
  )
}

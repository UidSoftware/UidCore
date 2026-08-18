import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2, Search, Store, ClipboardList } from 'lucide-react'
import api from '../api/client.js'
import { extractErrorMessage, stripEmptyStrings } from '../utils/errors.js'
import Card from '../components/ui/Card.jsx'
import Button from '../components/ui/Button.jsx'
import Input from '../components/ui/Input.jsx'
import Select from '../components/ui/Select.jsx'
import Modal from '../components/ui/Modal.jsx'
import Pagination from '../components/ui/Pagination.jsx'

const PAGE_SIZE = 10

const TABS = [
  { key: 'orcamentos', label: 'Orcamentos' },
  { key: 'pedidos', label: 'Pedidos' },
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
  { value: 'EM_PRODUCAO', label: 'Em Producao' },
  { value: 'ENTREGUE', label: 'Entregue' },
  { value: 'CANCELADO', label: 'Cancelado' },
]

const BRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

const EMPTY_ITEM = { produto: null, produto_nome: '', descricao: '', quantidade: 1, valor_unitario: '', valor_total: 0 }

// --- Autocomplete de produto ---
// onInvalidate: chamado quando o usuario edita o texto apos ja ter selecionado
// um produto — sinaliza para o pai limpar produto_id e valor_unitario
function ProdutoAutocomplete({ value, onChange, onSelect, onInvalidate }) {
  const [query, setQuery] = useState(value || '')
  const [opcoes, setOpcoes] = useState([])
  const [aberto, setAberto] = useState(false)
  const [erroBusca, setErroBusca] = useState(null)
  const [dropdownStyle, setDropdownStyle] = useState({})
  const debounceRef = useRef(null)
  const abortRef = useRef(null)   // Fix 1: AbortController para cancelar requests anteriores
  const selecionadoRef = useRef(false) // Fix 3: rastreia se ha produto selecionado vinculado
  const wrapRef = useRef(null)
  const inputRef = useRef(null)   // Fix M32: ref no input para getBoundingClientRect

  useEffect(() => {
    setQuery(value || '')
  }, [value])

  // Fix M32: calcula posicao fixed para escapar overflow do Modal
  const calcularPosicao = useCallback(() => {
    if (!inputRef.current) return
    const rect = inputRef.current.getBoundingClientRect()
    setDropdownStyle({
      position: 'fixed',
      top: rect.bottom + 4,
      left: rect.left,
      width: rect.width,
      zIndex: 9999,
    })
  }, [])

  // Recalcula ao abrir o dropdown
  useEffect(() => {
    if (aberto) calcularPosicao()
  }, [aberto, calcularPosicao])

  // Reposiciona ao rolar ou redimensionar enquanto dropdown esta aberto
  useEffect(() => {
    if (!aberto) return
    window.addEventListener('scroll', calcularPosicao, true)
    window.addEventListener('resize', calcularPosicao)
    return () => {
      window.removeEventListener('scroll', calcularPosicao, true)
      window.removeEventListener('resize', calcularPosicao)
    }
  }, [aberto, calcularPosicao])

  const buscar = (termo) => {
    clearTimeout(debounceRef.current)
    if (!termo || termo.length < 2) {
      setOpcoes([])
      setAberto(false)
      setErroBusca(null)
      return
    }
    debounceRef.current = setTimeout(() => {
      // Fix 1: cancelar request anterior antes de disparar novo
      if (abortRef.current) abortRef.current.abort()
      const controller = new AbortController()
      abortRef.current = controller

      setErroBusca(null)
      api.get('/produtos/', { params: { search: termo, page_size: 10 }, signal: controller.signal })
        .then((r) => {
          setOpcoes(r.data.results || r.data || [])
          setAberto(true)
        })
        .catch((err) => {
          // Fix 2: ignorar CanceledError (abort intencional); mostrar erro real
          if (err.name === 'CanceledError' || err.name === 'AbortError' || err.code === 'ERR_CANCELED') return
          setOpcoes([])
          setAberto(false)
          setErroBusca('Erro ao buscar produtos. Tente novamente.')
        })
    }, 300)
  }

  const handleInput = (e) => {
    const v = e.target.value
    setQuery(v)
    // Fix 3: se havia produto selecionado e o usuario editou o texto manualmente,
    // invalidar o vinculo para evitar envio com produto_id desatualizado
    if (selecionadoRef.current) {
      selecionadoRef.current = false
      if (onInvalidate) onInvalidate()
    }
    onChange(v)
    buscar(v)
  }

  const handleSelect = (produto) => {
    selecionadoRef.current = true
    setQuery(produto.nome)
    setAberto(false)
    setErroBusca(null)
    onSelect(produto)
  }

  // Fechar ao clicar fora
  useEffect(() => {
    const handler = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setAberto(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={wrapRef} className="relative">
      <label className="text-sm font-medium text-gray-700 block mb-1 dark:text-slate-300">Produto</label>
      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={handleInput}
        placeholder="Buscar produto..."
        className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500"
      />
      {/* Fix 2: mensagem de erro visivel ao usuario */}
      {erroBusca && (
        <p className="text-xs text-red-600 mt-1 dark:text-red-400">{erroBusca}</p>
      )}
      {/* Fix M32: position fixed para escapar overflow-y-auto do Modal — dropdown nao e mais clipado */}
      {aberto && opcoes.length > 0 && (
        <div
          style={dropdownStyle}
          className="bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto dark:bg-navy-800 dark:border-navy-600 dark:shadow-none"
        >
          {opcoes.map((p) => (
            <button
              key={p.id}
              type="button"
              onMouseDown={() => handleSelect(p)}
              className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex justify-between items-center dark:hover:bg-navy-700"
            >
              <span className="font-medium text-gray-800 dark:text-slate-200">{p.nome}</span>
              <span className="text-xs text-gray-400 ml-2 dark:text-slate-500">{BRL(p.preco_venda)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// --- Busca rapida de produto (RF-02/RF-03/RF-06 — Manutencao 32) ---
// Campo unico acima da lista de itens, mesmo padrao do PDV (FrenteDeCaixa.jsx):
// buscar -> clicar -> item ja entra na lista, sem precisar de "+ Adicionar Item" antes.
function BuscaProdutoRapida({ onAdicionar }) {
  const [buscaRapida, setBuscaRapida] = useState('')
  const [resultadosRapida, setResultadosRapida] = useState([])
  const [buscandoRapida, setBuscandoRapida] = useState(false)
  const [dropdownStyleRapida, setDropdownStyleRapida] = useState({})
  const buscaRapidaRef = useRef(null)
  const wrapRef = useRef(null)
  const debounceRef = useRef(null)
  const abortRef = useRef(null)

  const abertoRapida = resultadosRapida.length > 0 || buscandoRapida

  // Mesma tecnica de posicionamento do ProdutoAutocomplete (Fix M32) — escapa o
  // overflow-y-auto do Modal.
  const calcularPosicaoRapida = useCallback(() => {
    if (!buscaRapidaRef.current) return
    const rect = buscaRapidaRef.current.getBoundingClientRect()
    setDropdownStyleRapida({
      position: 'fixed',
      top: rect.bottom + 4,
      left: rect.left,
      width: rect.width,
      zIndex: 9999,
    })
  }, [])

  useEffect(() => {
    if (abertoRapida) calcularPosicaoRapida()
  }, [abertoRapida, calcularPosicaoRapida])

  useEffect(() => {
    if (!abertoRapida) return
    window.addEventListener('scroll', calcularPosicaoRapida, true)
    window.addEventListener('resize', calcularPosicaoRapida)
    return () => {
      window.removeEventListener('scroll', calcularPosicaoRapida, true)
      window.removeEventListener('resize', calcularPosicaoRapida)
    }
  }, [abertoRapida, calcularPosicaoRapida])

  const dispararBusca = useCallback((termo) => {
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller
    return api.get('/produtos/', { params: { search: termo, page_size: 10 }, signal: controller.signal })
  }, [])

  // RF-02: sem minimo de caracteres — dispara com qualquer texto nao vazio (diferente
  // do ProdutoAutocomplete de linha, que exige 2+).
  useEffect(() => {
    clearTimeout(debounceRef.current)
    if (!buscaRapida.trim()) {
      setResultadosRapida([])
      setBuscandoRapida(false)
      return
    }
    debounceRef.current = setTimeout(() => {
      setBuscandoRapida(true)
      dispararBusca(buscaRapida.trim())
        .then((r) => setResultadosRapida(r.data.results || r.data || []))
        .catch((err) => {
          if (err.name === 'CanceledError' || err.name === 'AbortError' || err.code === 'ERR_CANCELED') return
          setResultadosRapida([])
        })
        .finally(() => setBuscandoRapida(false))
    }, 300)
    return () => clearTimeout(debounceRef.current)
  }, [buscaRapida, dispararBusca])

  const handleSelecionarRapida = (produto) => {
    if (abortRef.current) abortRef.current.abort()
    onAdicionar(produto)
    setBuscaRapida('')
    setResultadosRapida([])
    setBuscandoRapida(false)
  }

  // RF-06 (Could): Enter com match exato de codigo_barras adiciona direto — mesmo
  // padrao de handleBuscaKeyDown em FrenteDeCaixa.jsx.
  const handleKeyDownRapida = async (e) => {
    if (e.key !== 'Enter') return
    const termo = buscaRapida.trim()
    if (!termo) return

    const exatosAtuais = resultadosRapida.filter((p) => p.codigo_barras === termo)
    if (exatosAtuais.length === 1) {
      handleSelecionarRapida(exatosAtuais[0])
      return
    }

    clearTimeout(debounceRef.current)
    setBuscandoRapida(true)
    try {
      const r = await dispararBusca(termo)
      const lista = r.data.results || r.data || []
      setResultadosRapida(lista)
      const exatos = lista.filter((p) => p.codigo_barras === termo)
      if (exatos.length === 1) {
        handleSelecionarRapida(exatos[0])
      }
    } catch (err) {
      if (err.name === 'CanceledError' || err.name === 'AbortError' || err.code === 'ERR_CANCELED') return
      setResultadosRapida([])
    } finally {
      setBuscandoRapida(false)
    }
  }

  // Fechar ao clicar fora — mesmo padrao do ProdutoAutocomplete
  useEffect(() => {
    const handler = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        if (abortRef.current) abortRef.current.abort()
        setResultadosRapida([])
        setBuscandoRapida(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={wrapRef} className="relative mb-3">
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-slate-500 pointer-events-none" />
        <input
          ref={buscaRapidaRef}
          type="text"
          value={buscaRapida}
          onChange={(e) => setBuscaRapida(e.target.value)}
          onKeyDown={handleKeyDownRapida}
          placeholder="Buscar produto para adicionar..."
          className="w-full rounded-lg border border-gray-300 bg-white pl-9 pr-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500"
          autoComplete="off"
        />
      </div>
      {abertoRapida && (
        <div
          style={dropdownStyleRapida}
          className="bg-white rounded-lg shadow-lg border border-gray-200 max-h-64 overflow-y-auto dark:bg-navy-800 dark:border-navy-600 dark:shadow-none"
        >
          {buscandoRapida && (
            <div className="px-4 py-3 text-sm text-gray-400 dark:text-slate-500 text-center">Buscando...</div>
          )}
          {!buscandoRapida && resultadosRapida.map((p) => (
            <button
              key={p.id}
              type="button"
              onMouseDown={() => handleSelecionarRapida(p)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-0 text-left transition-colors dark:hover:bg-navy-700 dark:border-navy-700"
            >
              <div className={parseFloat(p.quantidade_estoque || 0) <= 0 ? 'opacity-50' : ''}>
                <p className="text-sm font-medium text-gray-900 dark:text-slate-100">{p.nome}</p>
                {p.codigo_barras && (
                  <p className="text-xs text-gray-400 dark:text-slate-500">{p.codigo_barras}</p>
                )}
              </div>
              <div className="text-right shrink-0 ml-3">
                <p className="text-sm font-mono font-medium text-gray-900 dark:text-slate-100">{BRL(p.preco_venda)}</p>
                {parseFloat(p.quantidade_estoque || 0) <= 0 ? (
                  <span className="px-1.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">
                    Sem estoque
                  </span>
                ) : (
                  <p className="text-xs text-gray-400 dark:text-slate-500">{p.quantidade_estoque} {p.unidade_base}</p>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// --- Secao de Itens ---
function SecaoItens({ itens, setItens }) {
  const totalGeral = itens.reduce((s, it) => s + (Number(it.valor_total) || 0), 0)

  const addItem = () => {
    setItens((prev) => [...prev, { ...EMPTY_ITEM }])
  }

  // RF-03: selecionar no campo de busca rapida cria a linha ja preenchida,
  // sem precisar clicar em "+ Adicionar Item" antes — espelha o fluxo do PDV.
  const adicionarItemComProduto = (produto) => {
    const preco = Number(produto.preco_venda || 0)
    setItens((prev) => [
      ...prev,
      {
        produto: produto.id,
        produto_nome: produto.nome,
        descricao: produto.nome,
        quantidade: 1,
        valor_unitario: String(preco),
        valor_total: Number((1 * preco).toFixed(2)),
      },
    ])
  }

  const removeItem = (idx) => {
    setItens((prev) => prev.filter((_, i) => i !== idx))
  }

  const updateItem = (idx, field, value) => {
    setItens((prev) =>
      prev.map((it, i) => {
        if (i !== idx) return it
        const updated = { ...it, [field]: value }
        // Recalcular valor_total
        const qtd = Number(field === 'quantidade' ? value : updated.quantidade) || 0
        const unit = Number(field === 'valor_unitario' ? value : updated.valor_unitario) || 0
        updated.valor_total = (qtd * unit).toFixed(2)
        return updated
      })
    )
  }

  const handleSelectProduto = (idx, produto) => {
    setItens((prev) =>
      prev.map((it, i) => {
        if (i !== idx) return it
        const qtd = Number(it.quantidade) || 1
        const unit = Number(produto.preco_venda) || 0
        return {
          ...it,
          produto: produto.id,
          produto_nome: produto.nome,
          descricao: produto.nome,
          valor_unitario: String(unit),
          valor_total: (qtd * unit).toFixed(2),
        }
      })
    )
  }

  // Fix 3: chamado quando usuario edita o texto apos selecionar produto
  // limpa produto_id e valor_unitario para evitar envio com dados inconsistentes
  const handleInvalidateProduto = (idx) => {
    setItens((prev) =>
      prev.map((it, i) => {
        if (i !== idx) return it
        return {
          ...it,
          produto: null,
          valor_unitario: '',
          valor_total: 0,
        }
      })
    )
  }

  return (
    <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 dark:bg-navy-900/50 dark:border-navy-700">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">Itens</h3>
        <button
          type="button"
          onClick={addItem}
          className="text-xs text-primary-600 font-medium hover:text-primary-800 transition-colors dark:text-violet-400 dark:hover:text-violet-300"
        >
          + Adicionar Item
        </button>
      </div>

      <BuscaProdutoRapida onAdicionar={adicionarItemComProduto} />

      {itens.length === 0 && (
        <p className="text-xs text-gray-400 dark:text-slate-500">Nenhum item adicionado.</p>
      )}

      <div className="space-y-3">
        {itens.map((it, idx) => (
          <div key={idx} className="bg-white rounded-lg border border-gray-200 p-3 space-y-2 dark:bg-navy-800 dark:border-navy-600">
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => removeItem(idx)}
                className="text-red-400 hover:text-red-600 transition-colors dark:text-red-400/70 dark:hover:text-red-400"
              >
                <Trash2 size={14} />
              </button>
            </div>
            <ProdutoAutocomplete
              value={it.produto_nome}
              onChange={(v) => updateItem(idx, 'produto_nome', v)}
              onSelect={(p) => handleSelectProduto(idx, p)}
              onInvalidate={() => handleInvalidateProduto(idx)}
            />
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Descricao</label>
              <input
                type="text"
                value={it.descricao}
                onChange={(e) => updateItem(idx, 'descricao', e.target.value)}
                placeholder="Descricao do item"
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500"
              />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div className="flex flex-col gap-1">
                <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Quantidade</label>
                <input
                  type="number"
                  min="0.001"
                  step="0.001"
                  value={it.quantidade}
                  onChange={(e) => updateItem(idx, 'quantidade', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:focus:ring-violet-500"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Valor Unit. (R$)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={it.valor_unitario}
                  onChange={(e) => updateItem(idx, 'valor_unitario', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:focus:ring-violet-500"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Total (R$)</label>
                <input
                  type="text"
                  readOnly
                  value={BRL(it.valor_total)}
                  className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 cursor-default dark:border-navy-700 dark:bg-navy-900 dark:text-slate-300"
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {itens.length > 0 && (
        <div className="mt-3 flex justify-end">
          <span className="text-sm font-bold text-gray-800 dark:text-slate-200">Total Geral: {BRL(totalGeral)}</span>
        </div>
      )}
    </div>
  )
}

// --- Orcamentos Tab ---
function OrcamentosTab({ showToast }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(EMPTY_ORCAMENTO)
  const [itens, setItens] = useState([])
  const [clientesOptions, setClientesOptions] = useState([])

  useEffect(() => {
    api.get('/clientes/', { params: { page_size: 200 } })
      .then((r) => {
        const list = (r.data.results || r.data || []).map((c) => ({
          value: c.id, label: c.nome_razao_social,
        }))
        setClientesOptions([{ value: '', label: 'Selecione...' }, ...list])
      })
      .catch(() => {})
  }, [])

  const fetch = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.get('/vendas/orcamentos/', { params: { search, page, page_size: PAGE_SIZE } })
      setItems(r.data.results || r.data || [])
      const count = r.data.count || (r.data.results || r.data || []).length
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
    } catch { showToast('Erro ao carregar orcamentos.', 'error') }
    finally { setLoading(false) }
  }, [search, page])

  useEffect(() => { fetch() }, [fetch])

  const handleChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }))

  const openNew = () => { setForm(EMPTY_ORCAMENTO); setItens([]); setEditingId(null); setModalOpen(true) }
  const openEdit = async (item) => {
    setForm({
      cliente: item.cliente || '',
      status: item.status || 'RASCUNHO',
      validade: item.validade || '',
      descricao: item.descricao || '',
      observacoes: item.observacoes || '',
    })
    setEditingId(item.id)
    setItens([])
    setModalOpen(true)
    try {
      const r = await api.get(`/vendas/orcamentos/${item.id}/itens/`)
      const lista = r.data.results || r.data || []
      setItens(lista.map((i) => ({
        id: i.id,
        produto: i.produto || null,
        produto_nome: i.produto_nome || '',
        descricao: i.descricao || '',
        quantidade: i.quantidade || 1,
        valor_unitario: i.valor_unitario || '',
        valor_total: i.valor_total || 0,
      })))
    } catch {
      // silencioso
    }
  }
  const closeModal = () => { setModalOpen(false); setEditingId(null); setItens([]) }

  const handleSubmit = async (e) => {
    e.preventDefault(); setSaving(true)
    try {
      const payload = stripEmptyStrings(form)
      let orcId = editingId
      if (editingId) {
        await api.patch(`/vendas/orcamentos/${editingId}/`, payload)
        showToast('Orcamento atualizado.')
      } else {
        const r = await api.post('/vendas/orcamentos/', payload)
        orcId = r.data.id
        showToast('Orcamento cadastrado.')
      }
      // Salvar itens novos
      if (orcId) {
        for (const it of itens) {
          if (!it.id) {
            const itemPayload = {
              produto: it.produto || null,
              descricao: it.descricao,
              quantidade: it.quantidade,
              valor_unitario: it.valor_unitario,
            }
            await api.post(`/vendas/orcamentos/${orcId}/itens/`, stripEmptyStrings(itemPayload)).catch(() => {})
          }
        }
      }
      closeModal(); fetch()
    } catch (error) { showToast(extractErrorMessage(error, 'Erro ao salvar orcamento.'), 'error') }
    finally { setSaving(false) }
  }

  const handleDelete = async (item) => {
    if (!window.confirm(`Excluir orcamento "${item.numero || item.id}"?`)) return
    try { await api.delete(`/vendas/orcamentos/${item.id}/`); showToast('Orcamento removido.'); fetch() }
    catch (error) { showToast(extractErrorMessage(error, 'Erro ao remover.'), 'error') }
  }

  const STATUS_BADGES = {
    RASCUNHO: 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400',
    ENVIADO: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    APROVADO: 'bg-green-100 text-green-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    REJEITADO: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    CANCELADO: 'bg-gray-100 text-gray-500 dark:bg-navy-700 dark:text-slate-500',
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-slate-200">Orcamentos</h2>
        <Button onClick={openNew}>+ Novo Orcamento</Button>
      </div>
      <Card>
        <Input placeholder="Buscar..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
      </Card>

      {loading ? (
        <div className="text-center py-12 text-gray-400 dark:text-slate-500 text-sm">Carregando...</div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400 dark:text-slate-500">
          <span className="text-4xl">📄</span>
          <p className="text-sm">Nenhum orcamento encontrado.</p>
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-3 md:hidden">
            {items.map((item) => (
              <Card key={item.id}>
                <div className="flex justify-between items-start gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-gray-900 truncate dark:text-slate-100">{item.numero || `#${item.id}`}</p>
                    <p className="text-xs text-gray-500 mt-0.5 dark:text-slate-400">{item.cliente_nome || '—'}</p>
                  </div>
                  <span className={`shrink-0 text-xs rounded-full px-2 py-0.5 font-semibold ${STATUS_BADGES[item.status] || 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400'}`}>
                    {item.status}
                  </span>
                </div>
                <div className="mt-2 flex justify-between items-center">
                  <span className="text-lg font-bold text-gray-900 dark:text-slate-100">{BRL(item.valor_total)}</span>
                  <span className="text-xs text-gray-400 dark:text-slate-500">{item.validade || '—'}</span>
                </div>
                <div className="mt-3 flex gap-2">
                  <Button size="sm" variant="secondary" onClick={() => openEdit(item)}>Editar</Button>
                  <Button size="sm" variant="danger" onClick={() => handleDelete(item)}>Excluir</Button>
                </div>
              </Card>
            ))}
          </div>
          <div className="hidden md:block">
            <Card>
              <div className="overflow-x-auto -mx-6 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200 dark:bg-navy-900 dark:border-navy-600">
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Numero</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Cliente</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Valor</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Status</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Validade</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Acoes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-navy-700">
                    {items.map((item) => (
                      <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-navy-700/60">
                        <td className="px-4 py-3 font-medium text-gray-900 dark:text-slate-100">{item.numero || `#${item.id}`}</td>
                        <td className="px-4 py-3 text-gray-600 dark:text-slate-400">{item.cliente_nome || '—'}</td>
                        <td className="px-4 py-3 text-right font-semibold text-gray-900 dark:text-slate-100">{BRL(item.valor_total)}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs rounded-full px-2 py-0.5 font-semibold ${STATUS_BADGES[item.status] || 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400'}`}>
                            {item.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-600 dark:text-slate-400">{item.validade || '—'}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end gap-2">
                            <Button size="sm" variant="secondary" onClick={() => openEdit(item)}>Editar</Button>
                            <Button size="sm" variant="danger" onClick={() => handleDelete(item)}>Excluir</Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}

      {modalOpen && (
        <Modal title={editingId ? 'Editar Orcamento' : 'Novo Orcamento'} onClose={closeModal} maxW="max-w-2xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Select label="Cliente" name="cliente" options={clientesOptions} value={form.cliente} onChange={handleChange} />
              <Select label="Status" name="status" options={STATUS_ORCAMENTO} value={form.status} onChange={handleChange} />
            </div>
            <Input label="Validade" name="validade" type="date" value={form.validade} onChange={handleChange} />
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Descricao</label>
              <textarea name="descricao" value={form.descricao} onChange={handleChange} rows={2}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500" />
            </div>

            <SecaoItens itens={itens} setItens={setItens} />

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Observacoes</label>
              <textarea name="observacoes" value={form.observacoes} onChange={handleChange} rows={2}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500" />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={closeModal}>Cancelar</Button>
              <Button type="submit" loading={saving}>{editingId ? 'Salvar' : 'Cadastrar'}</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

const EMPTY_ORCAMENTO = {
  cliente: '', status: 'RASCUNHO', validade: '', descricao: '', observacoes: '',
}

// --- Pedidos Tab ---
function PedidosTab({ showToast }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(EMPTY_PEDIDO)
  const [itens, setItens] = useState([])
  const [clientesOptions, setClientesOptions] = useState([])

  useEffect(() => {
    api.get('/clientes/', { params: { page_size: 200 } })
      .then((r) => {
        const list = (r.data.results || r.data || []).map((c) => ({
          value: c.id, label: c.nome_razao_social,
        }))
        setClientesOptions([{ value: '', label: 'Selecione...' }, ...list])
      })
      .catch(() => {})
  }, [])

  const fetch = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.get('/vendas/pedidos/', { params: { search, page, page_size: PAGE_SIZE } })
      setItems(r.data.results || r.data || [])
      const count = r.data.count || (r.data.results || r.data || []).length
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
    } catch { showToast('Erro ao carregar pedidos.', 'error') }
    finally { setLoading(false) }
  }, [search, page])

  useEffect(() => { fetch() }, [fetch])

  const handleChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }))

  const openNew = () => { setForm(EMPTY_PEDIDO); setItens([]); setEditingId(null); setModalOpen(true) }
  const openEdit = async (item) => {
    setForm({
      cliente: item.cliente || '',
      status: item.status || 'PENDENTE',
      data_pedido: item.data_pedido || '',
      data_entrega_prevista: item.data_entrega_prevista || '',
      observacoes: item.observacoes || '',
    })
    setEditingId(item.id)
    setItens([])
    setModalOpen(true)
    try {
      const r = await api.get(`/vendas/pedidos/${item.id}/itens/`)
      const lista = r.data.results || r.data || []
      setItens(lista.map((i) => ({
        id: i.id,
        produto: i.produto || null,
        produto_nome: i.produto_nome || '',
        descricao: i.descricao || '',
        quantidade: i.quantidade || 1,
        valor_unitario: i.valor_unitario || '',
        valor_total: i.valor_total || 0,
      })))
    } catch {
      // silencioso
    }
  }
  const closeModal = () => { setModalOpen(false); setEditingId(null); setItens([]) }

  const handleSubmit = async (e) => {
    e.preventDefault(); setSaving(true)
    try {
      const payload = stripEmptyStrings(form)
      let pedidoId = editingId
      if (editingId) {
        await api.patch(`/vendas/pedidos/${editingId}/`, payload)
        showToast('Pedido atualizado.')
      } else {
        const r = await api.post('/vendas/pedidos/', payload)
        pedidoId = r.data.id
        showToast('Pedido cadastrado.')
      }
      if (pedidoId) {
        for (const it of itens) {
          if (!it.id) {
            const itemPayload = {
              produto: it.produto || null,
              descricao: it.descricao,
              quantidade: it.quantidade,
              valor_unitario: it.valor_unitario,
            }
            await api.post(`/vendas/pedidos/${pedidoId}/itens/`, stripEmptyStrings(itemPayload)).catch(() => {})
          }
        }
      }
      closeModal(); fetch()
    } catch (error) { showToast(extractErrorMessage(error, 'Erro ao salvar pedido.'), 'error') }
    finally { setSaving(false) }
  }

  const handleDelete = async (item) => {
    if (!window.confirm(`Excluir pedido "${item.numero || item.id}"?`)) return
    try { await api.delete(`/vendas/pedidos/${item.id}/`); showToast('Pedido removido.'); fetch() }
    catch (error) { showToast(extractErrorMessage(error, 'Erro ao remover.'), 'error') }
  }

  const STATUS_BADGES = {
    PENDENTE: 'bg-yellow-100 text-yellow-800 dark:bg-amber-900/30 dark:text-amber-300',
    CONFIRMADO: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    EM_PRODUCAO: 'bg-purple-100 text-purple-700 dark:bg-violet-900/30 dark:text-violet-300',
    ENTREGUE: 'bg-green-100 text-green-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    CANCELADO: 'bg-gray-100 text-gray-500 dark:bg-navy-700 dark:text-slate-500',
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-slate-200">Pedidos</h2>
        <Button onClick={openNew}>+ Novo Pedido</Button>
      </div>
      <Card>
        <Input placeholder="Buscar..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
      </Card>

      {loading ? (
        <div className="text-center py-12 text-gray-400 dark:text-slate-500 text-sm">Carregando...</div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400 dark:text-slate-500">
          <span className="text-4xl">🛒</span>
          <p className="text-sm">Nenhum pedido encontrado.</p>
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-3 md:hidden">
            {items.map((item) => (
              <Card key={item.id}>
                <div className="flex justify-between items-start gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-gray-900 truncate dark:text-slate-100">{item.numero || `#${item.id}`}</p>
                    <p className="text-xs text-gray-500 mt-0.5 dark:text-slate-400">{item.cliente_nome || '—'}</p>
                  </div>
                  <span className={`shrink-0 text-xs rounded-full px-2 py-0.5 font-semibold ${STATUS_BADGES[item.status] || 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400'}`}>
                    {item.status}
                  </span>
                </div>
                <div className="mt-2 flex justify-between items-center">
                  <span className="text-lg font-bold text-gray-900 dark:text-slate-100">{BRL(item.valor_total)}</span>
                  <span className="text-xs text-gray-400 dark:text-slate-500">{item.data_entrega_prevista || '—'}</span>
                </div>
                <div className="mt-3 flex gap-2">
                  <Button size="sm" variant="secondary" onClick={() => openEdit(item)}>Editar</Button>
                  <Button size="sm" variant="danger" onClick={() => handleDelete(item)}>Excluir</Button>
                </div>
              </Card>
            ))}
          </div>
          <div className="hidden md:block">
            <Card>
              <div className="overflow-x-auto -mx-6 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200 dark:bg-navy-900 dark:border-navy-600">
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Numero</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Cliente</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Valor</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Status</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Entrega Prevista</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Acoes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-navy-700">
                    {items.map((item) => (
                      <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-navy-700/60">
                        <td className="px-4 py-3 font-medium text-gray-900 dark:text-slate-100">{item.numero || `#${item.id}`}</td>
                        <td className="px-4 py-3 text-gray-600 dark:text-slate-400">{item.cliente_nome || '—'}</td>
                        <td className="px-4 py-3 text-right font-semibold text-gray-900 dark:text-slate-100">{BRL(item.valor_total)}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs rounded-full px-2 py-0.5 font-semibold ${STATUS_BADGES[item.status] || 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400'}`}>
                            {item.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-600 dark:text-slate-400">{item.data_entrega_prevista || '—'}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end gap-2">
                            <Button size="sm" variant="secondary" onClick={() => openEdit(item)}>Editar</Button>
                            <Button size="sm" variant="danger" onClick={() => handleDelete(item)}>Excluir</Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}

      {modalOpen && (
        <Modal title={editingId ? 'Editar Pedido' : 'Novo Pedido'} onClose={closeModal} maxW="max-w-2xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Select label="Cliente" name="cliente" options={clientesOptions} value={form.cliente} onChange={handleChange} />
              <Select label="Status" name="status" options={STATUS_PEDIDO} value={form.status} onChange={handleChange} />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input label="Data do Pedido" name="data_pedido" type="date" value={form.data_pedido} onChange={handleChange} />
              <Input label="Entrega Prevista" name="data_entrega_prevista" type="date" value={form.data_entrega_prevista} onChange={handleChange} />
            </div>

            <SecaoItens itens={itens} setItens={setItens} />

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Observacoes</label>
              <textarea name="observacoes" value={form.observacoes} onChange={handleChange} rows={2}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500" />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={closeModal}>Cancelar</Button>
              <Button type="submit" loading={saving}>{editingId ? 'Salvar' : 'Cadastrar'}</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

const EMPTY_PEDIDO = {
  cliente: '', status: 'PENDENTE', data_pedido: '', data_entrega_prevista: '', observacoes: '',
}

// --- Componente principal ---
export default function Vendas() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('orcamentos')
  const [toast, setToast] = useState(null)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), type === 'error' ? 7000 : 3500)
  }

  return (
    <div className="space-y-4">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white whitespace-pre-line break-words ${toast.type === 'error' ? 'bg-red-600' : 'bg-accent-600'}`}>
          {toast.msg}
        </div>
      )}

      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Vendas</h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-0.5">Orcamentos, pedidos e funil comercial</p>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="secondary" size="sm" onClick={() => navigate('/pdv')}>
          <Store size={16} />
          PDV
        </Button>
        <Button variant="secondary" size="sm" onClick={() => navigate('/pdv/sessoes')}>
          <ClipboardList size={16} />
          Caixas
        </Button>
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

      {tab === 'orcamentos' && <OrcamentosTab showToast={showToast} />}
      {tab === 'pedidos' && <PedidosTab showToast={showToast} />}
    </div>
  )
}

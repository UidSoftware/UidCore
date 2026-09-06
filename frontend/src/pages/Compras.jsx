import { useState, useEffect, useCallback, useRef } from 'react'
import { Search, Trash2, Eye, Ban } from 'lucide-react'
import api from '../api/client.js'
import { extractErrorMessage, stripEmptyStrings } from '../utils/errors.js'
import Card from '../components/ui/Card.jsx'
import Button from '../components/ui/Button.jsx'
import Input from '../components/ui/Input.jsx'
import Select from '../components/ui/Select.jsx'
import Modal from '../components/ui/Modal.jsx'
import Pagination from '../components/ui/Pagination.jsx'

const PAGE_SIZE = 10

// Mesmo catalogo fixo de unidades ja usado em Produtos.jsx (Fase 1) — Compras
// nao introduz nenhuma unidade nova, so reaproveita produtos.UnidadeBase.
const UNIDADE_OPTIONS = [
  { value: 'UN', label: 'UN — Unidade' },
  { value: 'PT', label: 'PT — Pacote' },
  { value: 'CX', label: 'CX — Caixa' },
  { value: 'KG', label: 'KG — Quilograma' },
  { value: 'L', label: 'L — Litro' },
  { value: 'M', label: 'M — Metro' },
]

const unidadeLabel = (valor) => UNIDADE_OPTIONS.find((u) => u.value === valor)?.label || valor

// Mesmo array ja definido em Financeiro.jsx — copiado, nao importado
// (mesmo padrao de duplicacao ja aceito no projeto, ver Especificacao_UI_Hotfix).
const FORMA_PAGAMENTO = [
  { value: '', label: 'Selecione...' },
  { value: 'PIX', label: 'PIX' },
  { value: 'TED_DOC', label: 'TED/DOC' },
  { value: 'BOLETO', label: 'Boleto' },
  { value: 'CARTAO_DEBITO', label: 'Cartão Débito' },
  { value: 'CARTAO_CREDITO', label: 'Cartão Crédito' },
  { value: 'DINHEIRO', label: 'Dinheiro' },
  { value: 'OUTRO', label: 'Outro' },
]

const FORMA_PAGAMENTO_LABEL = Object.fromEntries(FORMA_PAGAMENTO.map((f) => [f.value, f.label]))
const formaPagamentoLabel = (v) => FORMA_PAGAMENTO_LABEL[v] || v || '—'

const STATUS_FILTRO_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'PENDENTE', label: 'Pendente' },
  { value: 'PAGO', label: 'Pago' },
  { value: 'CANCELADO', label: 'Cancelado' },
]

// RN-06: "Cancelado" nunca aparece como opcao de Status Inicial na criacao —
// cancelamento e sempre via acao dedicada (RF-10), nunca via POST/PATCH direto.
const STATUS_INICIAL_OPTIONS = [
  { value: 'PENDENTE', label: 'Pendente' },
  { value: 'PAGO', label: 'Pago' },
]

// Badge de status — reaproveita 100% o padrao ja em producao em
// Financeiro.jsx (mesmas 3 chaves que Compra.status usa). Copiado, nao
// importado (mesmo padrao de duplicacao ja aceito no projeto).
const STATUS_BADGES = {
  PENDENTE: 'bg-yellow-100 text-yellow-800 dark:bg-amber-900/30 dark:text-amber-300',
  PAGO: 'bg-green-100 text-green-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  CANCELADO: 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400',
}

function Badge({ status }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${STATUS_BADGES[status] || 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400'}`}>
      {status}
    </span>
  )
}

const BRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

// Mesma implementacao ja usada em Marketing.jsx — evita shift de fuso-horario
// que `new Date(d).toLocaleDateString()` introduziria para campos DateField
// (sem hora) vindos do backend no formato "aaaa-mm-dd".
function formatData(d) {
  if (!d) return '—'
  const [ano, mes, dia] = d.split('-')
  return `${dia}/${mes}/${ano}`
}

const EMPTY_FORM = {
  fornecedor: '',
  conta: '',
  numero_nota_fiscal: '',
  data_emissao: '',
  forma_pagamento: '',
  status: 'PENDENTE',
  observacoes: '',
}

function InfoField({ label, value }) {
  return (
    <div>
      <p className="text-xs text-gray-400 dark:text-slate-500">{label}</p>
      <p className="text-gray-800 dark:text-slate-200">{value}</p>
    </div>
  )
}

// --- Busca rapida de produto (mesmo padrao de BuscaProdutoRapida em
// Vendas.jsx, Manutencao 32) — busca -> clicar -> item entra na lista, sem
// precisar de um botao "+ Adicionar Item" antes. Copiado sem alteracao de
// logica (mesmo padrao de reaproveitamento por copia ja usado entre
// Vendas/PDV — nao existe ainda modulo compartilhado de componentes de
// pagina, extrair e refinamento futuro fora de escopo desta fase).
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

  // Fix M32: position fixed para escapar overflow-y-auto do Modal.
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
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-slate-100">{p.nome}</p>
                {p.codigo_barras && (
                  <p className="text-xs text-gray-400 dark:text-slate-500">{p.codigo_barras}</p>
                )}
              </div>
              <div className="text-right shrink-0 ml-3">
                <p className="text-sm font-mono font-medium text-gray-900 dark:text-slate-100">{BRL(p.valor_unitario)}</p>
                <p className="text-xs text-gray-400 dark:text-slate-500">{p.quantidade_estoque || 0} {p.unidade_base}</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// --- Componente principal ---
export default function Compras() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [statusFiltro, setStatusFiltro] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [toast, setToast] = useState(null)

  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [itens, setItens] = useState([])

  const [detalheItem, setDetalheItem] = useState(null)

  const [fornecedoresOptions, setFornecedoresOptions] = useState([])
  const [contasOptions, setContasOptions] = useState([])

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), type === 'error' ? 7000 : 3500)
  }

  // Listas pre-carregadas para os Selects de Fornecedor/Conta — cadastros
  // pequenos/medios, mesmo padrao ja usado para Cliente/Conta em outras
  // telas (Vendas.jsx/Financeiro.jsx). Sem autocomplete de busca aqui.
  useEffect(() => {
    api.get('/fornecedores/', { params: { page_size: 200 } })
      .then((r) => {
        const list = (r.data.results || r.data || []).map((f) => ({
          value: f.id, label: f.nome_razao_social,
        }))
        setFornecedoresOptions([{ value: '', label: 'Selecione...' }, ...list])
      })
      .catch(() => {})

    api.get('/financeiro/contas/')
      .then((r) => {
        const list = (r.data.results || r.data || []).map((c) => ({
          value: c.id, label: c.nome,
        }))
        setContasOptions([{ value: '', label: 'Selecione...' }, ...list])
      })
      .catch(() => {})
  }, [])

  const fetch = useCallback(async () => {
    setLoading(true)
    try {
      const params = { search, page, page_size: PAGE_SIZE }
      if (statusFiltro) params.status = statusFiltro
      const r = await api.get('/compras/', { params })
      setItems(r.data.results || r.data || [])
      const count = r.data.count ?? (r.data.results || r.data || []).length
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
    } catch {
      showToast('Erro ao carregar compras.', 'error')
    } finally {
      setLoading(false)
    }
  }, [search, statusFiltro, page])

  useEffect(() => { fetch() }, [fetch])

  const openNovaCompra = () => {
    setForm(EMPTY_FORM)
    setItens([])
    setModalOpen(true)
  }

  const closeModal = () => {
    setModalOpen(false)
    setForm(EMPTY_FORM)
    setItens([])
  }

  const handleChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }))

  // RF-03/RF-05: clicar num resultado da busca rapida cria a linha ja
  // preenchida — unidade default = unidade_base do produto, valor unitario
  // de custo pre-preenchido com o ultimo custo conhecido (Produto.valor_unitario),
  // ajustavel antes de confirmar. `conversoes` ja vem junto no payload de
  // busca de produto (ProdutoSerializer sempre inclui o campo), usado para
  // popular o Select de Unidade sem nenhuma requisicao extra.
  const adicionarItemComProduto = (produto) => {
    setItens((prev) => [
      ...prev,
      {
        produto: produto.id,
        produto_nome: produto.nome,
        unidadeBase: produto.unidade_base || 'UN',
        conversoes: produto.conversoes || [],
        quantidade: '1',
        unidade: produto.unidade_base || 'UN',
        valor_unitario_custo: produto.valor_unitario ? String(produto.valor_unitario) : '',
        erroUnidade: null,
      },
    ])
  }

  const removeItem = (idx) => {
    setItens((prev) => prev.filter((_, i) => i !== idx))
  }

  const updateItem = (idx, field, value) => {
    setItens((prev) =>
      prev.map((it, i) => (i === idx ? { ...it, [field]: value, erroUnidade: field === 'unidade' ? null : it.erroUnidade } : it)),
    )
  }

  // Opcoes de unidade = unidade_base do produto + as unidades com conversao
  // cadastrada — mesmo padrao de resolucao de opcoes ja usado no campo de
  // conversao de Produtos.jsx.
  const unidadeOptionsDoProduto = (it) => {
    const base = it.unidadeBase || 'UN'
    const outras = (it.conversoes || [])
      .map((c) => c.unidade)
      .filter((u) => u && u !== base)
    const unicas = [...new Set(outras)]
    return [
      { value: base, label: `${unidadeLabel(base)} (base)` },
      ...unicas.map((u) => ({ value: u, label: unidadeLabel(u) })),
    ]
  }

  const totalGeral = itens.reduce(
    (s, it) => s + (Number(it.quantidade) || 0) * (Number(it.valor_unitario_custo) || 0),
    0,
  )

  const handleSubmit = async () => {
    if (itens.length === 0) return
    setSaving(true)
    try {
      const payload = stripEmptyStrings({
        fornecedor: form.fornecedor,
        conta: form.conta,
        numero_nota_fiscal: form.numero_nota_fiscal,
        data_emissao: form.data_emissao,
        forma_pagamento: form.forma_pagamento,
        status: form.status,
        observacoes: form.observacoes,
      })
      payload.itens = itens.map((it) => ({
        produto: it.produto,
        quantidade: it.quantidade,
        unidade: it.unidade,
        valor_unitario_custo: it.valor_unitario_custo,
      }))
      await api.post('/compras/', payload)
      showToast(
        form.status === 'PAGO'
          ? 'Compra registrada. Despesa gerada como Paga.'
          : 'Compra registrada. Despesa gerada como Pendente.',
      )
      closeModal()
      fetch()
    } catch (error) {
      const itensErr = error?.response?.data?.itens
      if (Array.isArray(itensErr)) {
        setItens((prev) =>
          prev.map((it, idx) => {
            const errObj = itensErr[idx]
            const erroUnidade = errObj && errObj.unidade
              ? (Array.isArray(errObj.unidade) ? errObj.unidade.join(' ') : String(errObj.unidade))
              : null
            return { ...it, erroUnidade }
          }),
        )
        showToast('Corrija os itens destacados.', 'error')
      } else {
        showToast(extractErrorMessage(error, 'Erro ao registrar compra.'), 'error')
      }
    } finally {
      setSaving(false)
    }
  }

  const confirmarCancelamento = async (item) => {
    if (!window.confirm(`Cancelar a compra de ${item.fornecedor_nome} no valor de ${BRL(item.valor_total)}?`)) return
    try {
      await api.post(`/compras/${item.id}/cancelar/`)
      showToast('Compra cancelada. Estoque revertido.')
      fetch()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao cancelar compra.'), 'error')
    }
  }

  return (
    <div className="space-y-4">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white whitespace-pre-line break-words ${toast.type === 'error' ? 'bg-red-600' : 'bg-accent-600'}`}>
          {toast.msg}
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Compras</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-0.5">Compras de mercadoria — fornecedor, estoque e financeiro integrados</p>
        </div>
        <Button onClick={openNovaCompra}>+ Nova Compra</Button>
      </div>

      <Card>
        <div className="flex flex-wrap gap-3">
          <div className="flex-1 min-w-[200px]">
            <Input
              placeholder="Buscar por NF ou fornecedor..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            />
          </div>
          <div className="w-48">
            <Select
              options={STATUS_FILTRO_OPTIONS}
              value={statusFiltro}
              onChange={(e) => { setStatusFiltro(e.target.value); setPage(1) }}
            />
          </div>
        </div>
      </Card>

      {loading ? (
        <div className="text-center py-12 text-gray-400 dark:text-slate-500 text-sm">Carregando...</div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400 dark:text-slate-500">
          <span className="text-4xl">📦</span>
          <p className="text-sm">Nenhuma compra registrada.</p>
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-3 md:hidden">
            {items.map((item) => (
              <Card key={item.id}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-medium text-gray-800 dark:text-slate-200 truncate">{item.fornecedor_nome}</p>
                    <p className="text-xs text-gray-400 dark:text-slate-500">
                      NF {item.numero_nota_fiscal || '—'} · {formatData(item.data_emissao)}
                    </p>
                  </div>
                  <Badge status={item.status} />
                </div>
                <div className="flex items-center justify-between mt-2">
                  <span className="font-semibold text-gray-800 dark:text-slate-200">{BRL(item.valor_total)}</span>
                  <div className="flex gap-3">
                    <button onClick={() => setDetalheItem(item)} className="text-gray-400 dark:text-slate-500">
                      <Eye size={16} />
                    </button>
                    {item.status !== 'CANCELADO' && (
                      <button onClick={() => confirmarCancelamento(item)} className="text-gray-400 dark:text-slate-500">
                        <Ban size={16} />
                      </button>
                    )}
                  </div>
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
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Fornecedor</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Nota Fiscal</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Data Emissão</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Valor Total</th>
                      <th className="text-center px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Status</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600 dark:text-slate-400">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-navy-700">
                    {items.map((item) => (
                      <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-navy-700/60">
                        <td className="px-4 py-3 font-medium text-gray-900 dark:text-slate-100">{item.fornecedor_nome}</td>
                        <td className="px-4 py-3 text-gray-600 dark:text-slate-400">{item.numero_nota_fiscal || '—'}</td>
                        <td className="px-4 py-3 text-gray-600 dark:text-slate-400">{formatData(item.data_emissao)}</td>
                        <td className="px-4 py-3 text-right font-medium text-gray-900 dark:text-slate-100">{BRL(item.valor_total)}</td>
                        <td className="px-4 py-3 text-center"><Badge status={item.status} /></td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end gap-3">
                            <button onClick={() => setDetalheItem(item)} title="Ver detalhes"
                              className="text-gray-400 hover:text-primary-600 transition-colors dark:text-slate-500 dark:hover:text-violet-400">
                              <Eye size={16} />
                            </button>
                            {item.status !== 'CANCELADO' && (
                              <button onClick={() => confirmarCancelamento(item)} title="Cancelar compra"
                                className="text-gray-400 hover:text-red-600 transition-colors dark:text-slate-500 dark:hover:text-red-400">
                                <Ban size={16} />
                              </button>
                            )}
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

      {/* Modal Nova Compra */}
      {modalOpen && (
        <Modal title="Nova Compra" onClose={closeModal} maxW="max-w-2xl">
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Select label="Fornecedor" name="fornecedor" options={fornecedoresOptions} value={form.fornecedor} onChange={handleChange} />
              <Select label="Conta" name="conta" options={contasOptions} value={form.conta} onChange={handleChange} />
              <Input label="Número da Nota Fiscal" name="numero_nota_fiscal" value={form.numero_nota_fiscal} onChange={handleChange} placeholder="NF-e 00001..." />
              <Input label="Data de Emissão" name="data_emissao" type="date" value={form.data_emissao} onChange={handleChange} />
              <Select label="Forma de Pagamento" name="forma_pagamento" options={FORMA_PAGAMENTO} value={form.forma_pagamento} onChange={handleChange} />
              <Select label="Status Inicial" name="status" options={STATUS_INICIAL_OPTIONS} value={form.status} onChange={handleChange} />
            </div>

            <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 dark:bg-navy-900/50 dark:border-navy-700">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">Itens</h3>
              </div>

              <BuscaProdutoRapida onAdicionar={adicionarItemComProduto} />

              {itens.length === 0 && (
                <p className="text-xs text-gray-400 dark:text-slate-500">Nenhum item adicionado.</p>
              )}

              <div className="space-y-3">
                {itens.map((it, idx) => (
                  <div key={idx} className="bg-white rounded-lg border border-gray-200 p-3 space-y-2 dark:bg-navy-800 dark:border-navy-600">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-gray-800 dark:text-slate-200 truncate">{it.produto_nome}</p>
                      <button type="button" onClick={() => removeItem(idx)}
                        className="text-red-400 hover:text-red-600 transition-colors dark:text-red-400/70 dark:hover:text-red-400 shrink-0">
                        <Trash2 size={14} />
                      </button>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      <Input label="Quantidade" type="number" min="0.001" step="0.001"
                        value={it.quantidade} onChange={(e) => updateItem(idx, 'quantidade', e.target.value)} />
                      <Select label="Unidade" options={unidadeOptionsDoProduto(it)}
                        value={it.unidade} onChange={(e) => updateItem(idx, 'unidade', e.target.value)} />
                      <Input label="Valor Unit. Custo (R$)" type="number" min="0.01" step="0.01"
                        value={it.valor_unitario_custo} onChange={(e) => updateItem(idx, 'valor_unitario_custo', e.target.value)} />
                      <div className="flex flex-col gap-1">
                        <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Subtotal</label>
                        <div className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-300">
                          {BRL((Number(it.quantidade) || 0) * (Number(it.valor_unitario_custo) || 0))}
                        </div>
                      </div>
                    </div>
                    {it.erroUnidade && (
                      <p className="text-xs text-red-600 dark:text-red-400">{it.erroUnidade}</p>
                    )}
                  </div>
                ))}
              </div>

              {itens.length > 0 && (
                <div className="mt-3 flex justify-end">
                  <span className="text-sm font-bold text-gray-800 dark:text-slate-200">
                    Total Geral: {BRL(totalGeral)}
                  </span>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Observações</label>
              <textarea name="observacoes" value={form.observacoes} onChange={handleChange} rows={2}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500" />
            </div>

            <div className="flex justify-end gap-2 mt-5">
              <Button variant="secondary" onClick={closeModal}>Cancelar</Button>
              <Button onClick={handleSubmit} loading={saving} disabled={saving || itens.length === 0}>
                {saving ? 'Salvando...' : 'Confirmar Compra'}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal Detalhe (read-only) — RN-05: sem edicao de compra existente */}
      {detalheItem && (
        <Modal title={`Compra #${detalheItem.id}`} onClose={() => setDetalheItem(null)}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm mb-4">
            <InfoField label="Fornecedor" value={detalheItem.fornecedor_nome} />
            <InfoField label="Conta" value={detalheItem.conta_nome} />
            <InfoField label="Nota Fiscal" value={detalheItem.numero_nota_fiscal || '—'} />
            <InfoField label="Data Emissão" value={formatData(detalheItem.data_emissao)} />
            <InfoField label="Forma de Pagamento" value={formaPagamentoLabel(detalheItem.forma_pagamento)} />
            <InfoField label="Status" value={<Badge status={detalheItem.status} />} />
          </div>

          {detalheItem.observacoes && (
            <p className="text-xs text-gray-500 dark:text-slate-400 mb-4">{detalheItem.observacoes}</p>
          )}

          <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200 mb-2">Itens</h3>
          <div className="space-y-2 mb-3">
            {(detalheItem.itens || []).map((it) => (
              <div key={it.id} className="flex items-center justify-between text-sm bg-gray-50 dark:bg-navy-900/50 rounded-lg px-3 py-2">
                <span className="text-gray-700 dark:text-slate-300">{it.produto_nome} — {it.quantidade} {it.unidade}</span>
                <span className="font-medium text-gray-800 dark:text-slate-200">{BRL(it.subtotal)}</span>
              </div>
            ))}
          </div>

          <div className="flex justify-between items-center border-t border-gray-200 dark:border-navy-700 pt-3">
            <span className="text-sm font-semibold text-gray-700 dark:text-slate-200">Total</span>
            <span className="text-sm font-bold text-gray-800 dark:text-slate-200">{BRL(detalheItem.valor_total)}</span>
          </div>

          {detalheItem.despesa && (
            <p className="text-xs text-gray-400 dark:text-slate-500 mt-3">
              Despesa vinculada: #{detalheItem.despesa} — ver em Financeiro
            </p>
          )}
        </Modal>
      )}
    </div>
  )
}

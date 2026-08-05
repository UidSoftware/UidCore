import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search, ScanLine, PackageSearch, User, UserX,
  CheckCircle2, ArrowDownCircle, ArrowUpCircle, Lock,
} from 'lucide-react'
import api from '../../api/client.js'
import { extractErrorMessage } from '../../utils/errors.js'
import Button from '../../components/ui/Button.jsx'
import Card from '../../components/ui/Card.jsx'
import CarrinhoItem from './components/CarrinhoItem.jsx'
import SplitPagamento from './components/SplitPagamento.jsx'
import ModalSangriaSuprimento from './components/ModalSangriaSuprimento.jsx'

const BRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

function formatarHora(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

export default function FrenteDeCaixa() {
  const navigate = useNavigate()

  // ── Sessão ──────────────────────────────────────────────────────────────
  const [sessao, setSessao] = useState(null)
  const [loadingSessao, setLoadingSessao] = useState(true)

  // ── Venda atual ─────────────────────────────────────────────────────────
  const [venda, setVenda] = useState(null)
  const [itens, setItens] = useState([])
  const [salvandoItem, setSalvandoItem] = useState(false)

  // ── Busca de produto ─────────────────────────────────────────────────────
  const [busca, setBusca] = useState('')
  const [resultadosBusca, setResultadosBusca] = useState([])
  const [buscando, setBuscando] = useState(false)
  const buscaRef = useRef(null)
  const debounceRef = useRef(null)

  // ── Cliente ──────────────────────────────────────────────────────────────
  const [clientes, setClientes] = useState([])
  const [clienteSelecionado, setClienteSelecionado] = useState(null)
  const [buscaCliente, setBuscaCliente] = useState('')
  const [resultadosCliente, setResultadosCliente] = useState([])
  const [mostrarBuscaCliente, setMostrarBuscaCliente] = useState(false)

  // ── Split de pagamento ───────────────────────────────────────────────────
  const [metodos, setMetodos] = useState([])
  const [contas, setContas] = useState([])
  const [linhasPagamento, setLinhasPagamento] = useState([])

  // ── UI ───────────────────────────────────────────────────────────────────
  const [finalizando, setFinalizando] = useState(false)
  const [modalSangria, setModalSangria] = useState(false)
  const [toast, setToast] = useState(null)

  const mostrarToast = (msg, tipo = 'success') => {
    setToast({ msg, tipo })
    setTimeout(() => setToast(null), tipo === 'error' ? 7000 : 3500)
  }

  // ── Carregar sessão ──────────────────────────────────────────────────────
  useEffect(() => {
    api.get('/pdv/sessoes/atual/')
      .then((res) => {
        setSessao(res.data)
      })
      .catch(() => {
        navigate('/pdv/abertura')
      })
      .finally(() => setLoadingSessao(false))
  }, [navigate])

  // ── Carregar metodos + contas ─────────────────────────────────────────────
  useEffect(() => {
    Promise.all([
      api.get('/pagamentos/metodos/?page_size=100'),
      api.get('/financeiro/contas/?page_size=100'),
    ]).then(([mRes, cRes]) => {
      setMetodos(mRes.data.results || mRes.data || [])
      setContas(cRes.data.results || cRes.data || [])
    }).catch(() => {})
  }, [])

  // ── Criar venda se não existir ────────────────────────────────────────────
  const criarVenda = useCallback(async () => {
    if (!sessao) return
    try {
      const { data } = await api.post('/pdv/vendas/', { sessao_caixa: sessao.id })
      setVenda(data)
      setItens([])
    } catch (err) {
      mostrarToast(extractErrorMessage(err, 'Erro ao criar venda.'), 'error')
    }
  }, [sessao])

  useEffect(() => {
    if (sessao && !venda) {
      criarVenda()
    }
  }, [sessao, venda, criarVenda])

  // ── Busca de produto com debounce ─────────────────────────────────────────
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!busca.trim()) {
      setResultadosBusca([])
      return
    }
    debounceRef.current = setTimeout(async () => {
      setBuscando(true)
      try {
        const { data } = await api.get(`/produtos/produtos/?search=${encodeURIComponent(busca)}&page_size=10`)
        setResultadosBusca(data.results || data || [])
      } catch {
        setResultadosBusca([])
      } finally {
        setBuscando(false)
      }
    }, 300)
    return () => clearTimeout(debounceRef.current)
  }, [busca])

  // ── Busca de cliente ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!buscaCliente.trim()) {
      setResultadosCliente([])
      return
    }
    const t = setTimeout(async () => {
      try {
        const { data } = await api.get(`/clientes/clientes/?search=${encodeURIComponent(buscaCliente)}&page_size=10`)
        setResultadosCliente(data.results || data || [])
      } catch {
        setResultadosCliente([])
      }
    }, 300)
    return () => clearTimeout(t)
  }, [buscaCliente])

  // ── Adicionar produto ao carrinho ─────────────────────────────────────────
  const adicionarProduto = async (produto) => {
    if (!venda) return
    setBusca('')
    setResultadosBusca([])
    setSalvandoItem(true)
    try {
      const { data: vendaAtualizada } = await api.post(`/pdv/vendas/${venda.id}/itens/`, {
        produto: produto.id,
        quantidade: '1.000',
        unidade: produto.unidade_base || 'UN',
        desconto_item: '0.00',
      })
      // Recarregar venda completa
      const { data: vendaFull } = await api.get(`/pdv/vendas/${venda.id}/`)
      setVenda(vendaFull)
      setItens(vendaFull.itens || [])
    } catch (err) {
      mostrarToast(extractErrorMessage(err, 'Erro ao adicionar produto.'), 'error')
    } finally {
      setSalvandoItem(false)
    }
  }

  // ── Alterar quantidade de item ────────────────────────────────────────────
  const handleQuantidade = async (itemId, novaQtd) => {
    if (!venda) return
    try {
      await api.patch(`/pdv/vendas/${venda.id}/itens/${itemId}/`, {
        quantidade: String(parseFloat(novaQtd).toFixed(3)),
      })
      const { data } = await api.get(`/pdv/vendas/${venda.id}/`)
      setVenda(data)
      setItens(data.itens || [])
    } catch (err) {
      mostrarToast(extractErrorMessage(err, 'Erro ao atualizar item.'), 'error')
    }
  }

  // ── Remover item ─────────────────────────────────────────────────────────
  const handleRemover = async (itemId) => {
    if (!venda) return
    try {
      await api.delete(`/pdv/vendas/${venda.id}/itens/${itemId}/`)
      const { data } = await api.get(`/pdv/vendas/${venda.id}/`)
      setVenda(data)
      setItens(data.itens || [])
    } catch (err) {
      mostrarToast(extractErrorMessage(err, 'Erro ao remover item.'), 'error')
    }
  }

  // ── Finalizar venda ──────────────────────────────────────────────────────
  const handleFinalizar = async () => {
    if (!venda) return
    if (linhasPagamento.length === 0) {
      mostrarToast('Adicione ao menos uma forma de pagamento.', 'error')
      return
    }

    const pagamentos = linhasPagamento.map((l) => {
      const p = {
        metodo: l.metodo_id,
        valor: l.valor,
      }
      if (l.conta) p.conta = parseInt(l.conta)
      if (l.metodo_cartao_credito) {
        if (l.taxa_percentual) p.taxa_percentual = l.taxa_percentual
        if (l.prazo_dias) p.prazo_dias = parseInt(l.prazo_dias)
      }
      return p
    })

    setFinalizando(true)
    try {
      await api.post(`/pdv/vendas/${venda.id}/finalizar/`, { pagamentos })
      mostrarToast('Venda finalizada com sucesso!')
      // Limpa e cria nova venda
      setVenda(null)
      setItens([])
      setLinhasPagamento([])
      setClienteSelecionado(null)
      // criarVenda será chamado via useEffect
    } catch (err) {
      mostrarToast(extractErrorMessage(err, 'Erro ao finalizar venda.'), 'error')
    } finally {
      setFinalizando(false)
    }
  }

  // ── Vincular cliente ─────────────────────────────────────────────────────
  const vincularCliente = async (cliente) => {
    if (!venda) return
    setClienteSelecionado(cliente)
    setMostrarBuscaCliente(false)
    setBuscaCliente('')
    try {
      await api.patch(`/pdv/vendas/${venda.id}/`, { cliente: cliente.id })
    } catch {
      // falha silenciosa — campo opcional
    }
  }

  const desvincularCliente = async () => {
    if (!venda) return
    setClienteSelecionado(null)
    try {
      await api.patch(`/pdv/vendas/${venda.id}/`, { cliente: null })
    } catch {
      // falha silenciosa
    }
  }

  const total = parseFloat(venda?.valor_total || 0)
  const itensAtivos = itens.filter((i) => i.is_active !== false)

  if (loadingSessao) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <p className="text-gray-400 text-sm">Carregando...</p>
      </div>
    )
  }

  return (
    <div className="space-y-4 pb-24 md:pb-6">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white whitespace-pre-line break-words ${
          toast.tipo === 'error' ? 'bg-red-600' : 'bg-accent-600'
        }`}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Nova Venda</h1>
          {sessao && (
            <p className="text-xs text-gray-500 mt-1">
              Sessão #{sessao.id} · {sessao.conta_nome || `Conta #${sessao.conta}`} · Aberta às {formatarHora(sessao.data_abertura)}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {sessao && (
            <button
              type="button"
              onClick={() => setModalSangria(true)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-300 bg-white text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <ArrowDownCircle size={14} className="text-red-600" />
              <ArrowUpCircle size={14} className="text-green-600" />
              Sangria/Suprimento
            </button>
          )}
          <button
            type="button"
            onClick={() => navigate('/pdv/fechamento')}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-300 bg-white text-sm text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <Lock size={14} />
            Fechar Caixa
          </button>
        </div>
      </div>

      {/* Layout desktop: 2 colunas */}
      <div className="flex flex-col md:flex-row gap-4 items-start">
        {/* Coluna esquerda: busca + carrinho */}
        <div className="flex-1 space-y-4 min-w-0">
          {/* Busca de produto */}
          <Card>
            <div className="relative">
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                  <input
                    ref={buscaRef}
                    type="text"
                    value={busca}
                    onChange={(e) => setBusca(e.target.value)}
                    placeholder="Buscar por nome ou código de barras..."
                    className="w-full rounded-lg border border-gray-300 bg-white pl-9 pr-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    autoFocus
                  />
                </div>
                <button
                  type="button"
                  onClick={() => buscaRef.current?.focus()}
                  className="p-2 rounded-lg border border-gray-300 text-gray-500 hover:bg-gray-50 transition-colors"
                  title="Focar para leitura de código de barras"
                >
                  <ScanLine size={16} />
                </button>
              </div>

              {/* Dropdown de resultados */}
              {(resultadosBusca.length > 0 || buscando) && (
                <div className="absolute z-10 left-0 right-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 max-h-64 overflow-y-auto">
                  {buscando && (
                    <div className="px-4 py-3 text-sm text-gray-400 text-center">Buscando...</div>
                  )}
                  {!buscando && resultadosBusca.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => adicionarProduto(p)}
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-0 text-left transition-colors"
                    >
                      <div className={parseFloat(p.quantidade_estoque || 0) <= 0 ? 'opacity-50' : ''}>
                        <p className="text-sm font-medium text-gray-900">{p.nome}</p>
                        {p.codigo_barras && (
                          <p className="text-xs text-gray-400">{p.codigo_barras}</p>
                        )}
                      </div>
                      <div className="text-right shrink-0 ml-3">
                        <p className="text-sm font-mono font-medium text-gray-900">{BRL(p.preco_venda)}</p>
                        {parseFloat(p.quantidade_estoque || 0) <= 0 ? (
                          <span className="px-1.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800">
                            Sem estoque
                          </span>
                        ) : (
                          <p className="text-xs text-gray-400">{p.quantidade_estoque} {p.unidade_base}</p>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </Card>

          {/* Carrinho */}
          <Card title="Carrinho">
            {itensAtivos.length === 0 ? (
              <div className="text-center py-12">
                <PackageSearch size={32} className="mx-auto text-gray-300 mb-2" />
                <p className="text-sm text-gray-400">Carrinho vazio — busque um produto acima</p>
              </div>
            ) : (
              <div>
                {itensAtivos.map((item) => (
                  <CarrinhoItem
                    key={item.id}
                    item={item}
                    onQuantidade={handleQuantidade}
                    onRemover={handleRemover}
                    disabled={salvandoItem}
                  />
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Coluna direita: cliente + resumo + pagamento */}
        <div className="w-full md:w-80 lg:w-96 space-y-4 md:sticky md:top-4 shrink-0">
          {/* Cliente */}
          <Card>
            <div className="space-y-2">
              {!clienteSelecionado ? (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <UserX size={16} className="text-gray-400" />
                    Consumidor Final
                  </div>
                  {!mostrarBuscaCliente && (
                    <button
                      type="button"
                      onClick={() => setMostrarBuscaCliente(true)}
                      className="text-primary-600 text-xs font-medium hover:underline"
                    >
                      Vincular cliente
                    </button>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-gray-900">
                    <User size={16} className="text-primary-600" />
                    <span className="font-medium">{clienteSelecionado.nome}</span>
                  </div>
                  <button
                    type="button"
                    onClick={desvincularCliente}
                    className="text-gray-400 hover:text-red-600 text-xs transition-colors"
                  >
                    Remover
                  </button>
                </div>
              )}

              {mostrarBuscaCliente && (
                <div className="relative">
                  <input
                    autoFocus
                    type="text"
                    value={buscaCliente}
                    onChange={(e) => setBuscaCliente(e.target.value)}
                    placeholder="Buscar cliente por nome..."
                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                  {resultadosCliente.length > 0 && (
                    <div className="absolute z-10 left-0 right-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 max-h-40 overflow-y-auto">
                      {resultadosCliente.map((c) => (
                        <button
                          key={c.id}
                          type="button"
                          onClick={() => vincularCliente(c)}
                          className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 border-b border-gray-100 last:border-0"
                        >
                          {c.nome}
                        </button>
                      ))}
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => { setMostrarBuscaCliente(false); setBuscaCliente('') }}
                    className="mt-1 text-xs text-gray-400 hover:text-gray-600"
                  >
                    Cancelar
                  </button>
                </div>
              )}
            </div>
          </Card>

          {/* Resumo de valores */}
          <Card>
            <div className="space-y-2">
              <div className="flex justify-between text-sm text-gray-600">
                <span>Subtotal</span>
                <span className="font-mono">{BRL(venda?.subtotal || 0)}</span>
              </div>
              {parseFloat(venda?.desconto_total || 0) > 0 && (
                <div className="flex justify-between text-sm text-gray-600">
                  <span>Desconto</span>
                  <span className="font-mono text-red-600">- {BRL(venda?.desconto_total || 0)}</span>
                </div>
              )}
              <div className="border-t border-gray-100 pt-2 flex justify-between">
                <span className="text-base font-bold text-gray-900">Total</span>
                <span className="text-lg font-bold text-gray-900 font-mono">{BRL(total)}</span>
              </div>
            </div>
          </Card>

          {/* Split de pagamento */}
          <Card title="Pagamento">
            <SplitPagamento
              metodos={metodos}
              contas={contas}
              total={total}
              linhas={linhasPagamento}
              onChange={setLinhasPagamento}
            />
          </Card>

          {/* Botão finalizar — desktop */}
          <div className="hidden md:block">
            <Button
              variant="primary"
              size="lg"
              className="w-full"
              loading={finalizando}
              disabled={itensAtivos.length === 0}
              onClick={handleFinalizar}
            >
              <CheckCircle2 size={16} className="mr-2" />
              Finalizar Venda — {BRL(total)}
            </Button>
          </div>
        </div>
      </div>

      {/* Barra fixa mobile */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4 z-40 md:hidden">
        <div className="flex items-center gap-3">
          <div className="flex-1">
            <p className="text-xs text-gray-500">Total</p>
            <p className="text-lg font-bold text-gray-900 font-mono">{BRL(total)}</p>
          </div>
          <Button
            variant="primary"
            size="lg"
            loading={finalizando}
            disabled={itensAtivos.length === 0}
            onClick={handleFinalizar}
            className="flex-1"
          >
            <CheckCircle2 size={16} className="mr-1.5" />
            Finalizar
          </Button>
        </div>
      </div>

      {/* Modal sangria/suprimento */}
      {modalSangria && sessao && (
        <ModalSangriaSuprimento
          sessaoId={sessao.id}
          onClose={() => setModalSangria(false)}
          onSucesso={() => {
            setModalSangria(false)
            mostrarToast('Movimento registrado com sucesso!')
          }}
        />
      )}
    </div>
  )
}

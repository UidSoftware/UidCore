import { useState, useEffect, useCallback } from 'react'
import api from '../api/client.js'
import { extractErrorMessage, stripEmptyStrings } from '../utils/errors.js'
import Card from '../components/ui/Card.jsx'
import Button from '../components/ui/Button.jsx'
import Input from '../components/ui/Input.jsx'
import Select from '../components/ui/Select.jsx'
import Modal from '../components/ui/Modal.jsx'
import Pagination from '../components/ui/Pagination.jsx'

const PAGE_SIZE = 20
const TABS = [
  { key: 'resumo', label: 'Resumo' },
  { key: 'receitas', label: 'Contas a Receber' },
  { key: 'despesas', label: 'Contas a Pagar' },
  { key: 'contas', label: 'Contas' },
  { key: 'livro', label: 'Livro Caixa' },
  { key: 'dre', label: 'DRE' },
  { key: 'balanco', label: 'Balanço' },
  { key: 'indicadores', label: 'Indicadores' },
]

const TIPO_RECEITA = [
  { value: 'SERVICO', label: 'Serviço' },
  { value: 'PRODUTO', label: 'Produto' },
  { value: 'MENSALIDADE', label: 'Mensalidade' },
  { value: 'RECEITA_FINANCEIRA', label: 'Receita Financeira' },
  { value: 'OUTRO', label: 'Outro' },
]

const TIPO_DESPESA = [
  { value: 'FIXA', label: 'Despesa Fixa' },
  { value: 'VARIAVEL', label: 'Despesa Variável' },
  { value: 'PROLABORE', label: 'Pró-labore' },
  { value: 'IMPOSTO', label: 'Imposto / DAS' },
  { value: 'OUTRO', label: 'Outro' },
]

const STATUS_RECEITA = [
  { value: '', label: 'Todos' },
  { value: 'PENDENTE', label: 'Pendente' },
  { value: 'RECEBIDO', label: 'Recebido' },
  { value: 'ATRASADO', label: 'Atrasado' },
  { value: 'CANCELADO', label: 'Cancelado' },
]

const STATUS_DESPESA = [
  { value: '', label: 'Todos' },
  { value: 'PENDENTE', label: 'Pendente' },
  { value: 'PAGO', label: 'Pago' },
  { value: 'ATRASADO', label: 'Atrasado' },
  { value: 'CANCELADO', label: 'Cancelado' },
]

const TIPO_CONTA = [
  { value: 'CORRENTE', label: 'Conta Corrente' },
  { value: 'POUPANCA', label: 'Poupança' },
  { value: 'CAIXA', label: 'Caixa' },
  { value: 'CARTEIRA', label: 'Carteira Digital' },
]

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

const STATUS_BADGES = {
  PENDENTE: 'bg-yellow-100 text-yellow-800',
  RECEBIDO: 'bg-green-100 text-green-800',
  PAGO: 'bg-green-100 text-green-800',
  ATRASADO: 'bg-red-100 text-red-800',
  CANCELADO: 'bg-gray-100 text-gray-600',
}

const BRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

function Badge({ status }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${STATUS_BADGES[status] || 'bg-gray-100 text-gray-600'}`}>
      {status}
    </span>
  )
}

export default function Financeiro() {
  const [tab, setTab] = useState('resumo')
  const [toast, setToast] = useState(null)
  const [contasOptions, setContasOptions] = useState([])

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), type === 'error' ? 7000 : 3500)
  }

  useEffect(() => {
    api.get('/financeiro/contas/').then((r) => {
      const list = (r.data.results || r.data || []).map((c) => ({
        value: c.id, label: c.nome,
      }))
      setContasOptions(list)
    }).catch(() => {})
  }, [])

  return (
    <div className="space-y-4">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white whitespace-pre-line break-words ${toast.type === 'error' ? 'bg-red-600' : 'bg-accent-600'}`}>
          {toast.msg}
        </div>
      )}

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Financeiro</h1>
        <p className="text-sm text-gray-500 mt-0.5">Gestão financeira completa</p>
      </div>

      <div className="flex gap-1 overflow-x-auto pb-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium rounded-lg whitespace-nowrap transition-colors ${
              tab === t.key
                ? 'bg-primary-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'resumo' && <ResumoTab />}
      {tab === 'receitas' && <ReceitasTab showToast={showToast} contasOptions={contasOptions} />}
      {tab === 'despesas' && <DespesasTab showToast={showToast} contasOptions={contasOptions} />}
      {tab === 'contas' && <ContasTab showToast={showToast} />}
      {tab === 'livro' && <LivroCaixaTab contasOptions={contasOptions} />}
      {tab === 'dre' && <DreTab />}
      {tab === 'balanco' && <BalancoTab />}
      {tab === 'indicadores' && <IndicadoresTab />}
    </div>
  )
}

function ResumoTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.get('/financeiro/dashboard/')
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-center py-12 text-gray-400">Carregando...</div>
  if (!data) return <div className="text-center py-12 text-gray-400">Erro ao carregar dados.</div>

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Saldo Total" value={BRL(data.saldo_total_contas)} color="blue" />
        <KpiCard label="Receita (mês)" value={BRL(data.receita_mes)} color="green" />
        <KpiCard label="Despesa (mês)" value={BRL(data.despesa_mes)} color="red" />
        <KpiCard label="Resultado" value={BRL(data.resultado_mes)} color={Number(data.resultado_mes) >= 0 ? 'green' : 'red'} />
      </div>

      {data.indicadores && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard label="MRR" value={BRL(data.indicadores.mrr)} color="blue" />
          <KpiCard label="Margem Líquida" value={`${data.indicadores.margem_liquida}%`} color={Number(data.indicadores.margem_liquida) >= 0 ? 'green' : 'red'} />
          <KpiCard label="Runway" value={`${data.indicadores.runway_meses} meses`} color={Number(data.indicadores.runway_meses) >= 6 ? 'green' : Number(data.indicadores.runway_meses) >= 3 ? 'blue' : 'red'} />
          <KpiCard label="Ponto Equilíbrio" value={BRL(data.indicadores.ponto_equilibrio)} color="blue" />
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card title="Receitas a Vencer (30 dias)">
          {data.receitas_vencer?.length === 0 ? (
            <p className="text-sm text-gray-400">Nenhuma receita pendente.</p>
          ) : (
            <div className="space-y-2">
              {data.receitas_vencer?.map((r, i) => (
                <div key={i} className="flex justify-between items-center text-sm">
                  <div className="min-w-0">
                    <p className="font-medium text-gray-800 truncate">{r.descricao}</p>
                    <p className="text-xs text-gray-400">{r.cliente__nome_razao_social || '—'} &middot; {r.vencimento}</p>
                  </div>
                  <span className="font-semibold text-green-700 whitespace-nowrap ml-2">{BRL(r.valor_liquido)}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Despesas a Vencer (30 dias)">
          {data.despesas_vencer?.length === 0 ? (
            <p className="text-sm text-gray-400">Nenhuma despesa pendente.</p>
          ) : (
            <div className="space-y-2">
              {data.despesas_vencer?.map((d, i) => (
                <div key={i} className="flex justify-between items-center text-sm">
                  <div className="min-w-0">
                    <p className="font-medium text-gray-800 truncate">{d.descricao}</p>
                    <p className="text-xs text-gray-400">{d.fornecedor || '—'} &middot; {d.vencimento}</p>
                  </div>
                  <span className="font-semibold text-red-700 whitespace-nowrap ml-2">{BRL(d.valor_liquido)}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {data.grafico_6_meses && (
        <Card title="Receita x Despesa (6 meses)">
          <div className="flex items-end gap-2 h-40">
            {data.grafico_6_meses.map((m) => {
              const max = Math.max(...data.grafico_6_meses.map((x) => Math.max(Number(x.receita), Number(x.despesa), 1)))
              const hRec = (Number(m.receita) / max) * 100
              const hDes = (Number(m.despesa) / max) * 100
              return (
                <div key={m.mes} className="flex-1 flex flex-col items-center gap-1">
                  <div className="flex gap-0.5 items-end h-32 w-full justify-center">
                    <div className="w-3 bg-green-400 rounded-t" style={{ height: `${hRec}%` }} title={BRL(m.receita)} />
                    <div className="w-3 bg-red-400 rounded-t" style={{ height: `${hDes}%` }} title={BRL(m.despesa)} />
                  </div>
                  <span className="text-[10px] text-gray-500">{m.label}</span>
                </div>
              )
            })}
          </div>
          <div className="flex gap-4 mt-2 text-xs text-gray-500">
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-green-400 rounded-full" />Receita</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-red-400 rounded-full" />Despesa</span>
          </div>
        </Card>
      )}
    </div>
  )
}

function KpiCard({ label, value, color }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-green-50 text-green-700',
    red: 'bg-red-50 text-red-700',
  }
  return (
    <div className={`rounded-xl p-4 ${colors[color] || colors.blue}`}>
      <p className="text-xs font-medium opacity-70">{label}</p>
      <p className="text-lg font-bold mt-1">{value}</p>
    </div>
  )
}

function ReceitasTab({ showToast, contasOptions }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(EMPTY_RECEITA)

  const fetch = useCallback(async () => {
    setLoading(true)
    try {
      const params = { search, page, page_size: PAGE_SIZE }
      if (statusFilter) params.status = statusFilter
      const r = await api.get('/financeiro/receitas/', { params })
      setItems(r.data.results || r.data || [])
      const count = r.data.count || (r.data.results || r.data || []).length
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
    } catch { showToast('Erro ao carregar receitas.', 'error') }
    finally { setLoading(false) }
  }, [search, statusFilter, page])

  useEffect(() => { fetch() }, [fetch])

  const handleChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }))

  const openNew = () => { setForm(EMPTY_RECEITA); setEditingId(null); setModalOpen(true) }
  const openEdit = (item) => {
    setForm({
      tipo: item.tipo || 'SERVICO', descricao: item.descricao || '',
      cliente: item.cliente || '', categoria: item.categoria || '',
      valor_bruto: item.valor_bruto || '', desconto: item.desconto || '0',
      conta: item.conta || '', vencimento: item.vencimento || '',
      observacoes: item.observacoes || '',
    })
    setEditingId(item.id); setModalOpen(true)
  }
  const closeModal = () => { setModalOpen(false); setEditingId(null) }

  const handleSubmit = async (e) => {
    e.preventDefault(); setSaving(true)
    try {
      const payload = stripEmptyStrings(form)
      if (editingId) {
        await api.patch(`/financeiro/receitas/${editingId}/`, payload)
        showToast('Receita atualizada.')
      } else {
        await api.post('/financeiro/receitas/', payload)
        showToast('Receita cadastrada.')
      }
      closeModal(); fetch()
    } catch (error) { showToast(extractErrorMessage(error, 'Erro ao salvar receita.'), 'error') }
    finally { setSaving(false) }
  }

  const marcarRecebido = async (item) => {
    try {
      await api.patch(`/financeiro/receitas/${item.id}/receber/`, {})
      showToast('Receita marcada como recebida.')
      fetch()
    } catch (error) { showToast(extractErrorMessage(error, 'Erro ao marcar recebimento.'), 'error') }
  }

  const handleDelete = async (item) => {
    if (!window.confirm(`Excluir "${item.descricao}"?`)) return
    try { await api.delete(`/financeiro/receitas/${item.id}/`); showToast('Receita removida.'); fetch() }
    catch (error) { showToast(extractErrorMessage(error, 'Erro ao remover.'), 'error') }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-800">Contas a Receber</h2>
        <Button onClick={openNew}>+ Nova Receita</Button>
      </div>

      <Card>
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <Input placeholder="Buscar..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
          </div>
          <div className="w-full sm:w-48">
            <Select options={STATUS_RECEITA} value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }} />
          </div>
        </div>
      </Card>

      {loading ? (
        <div className="text-center py-12 text-gray-400 text-sm">Carregando...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-400"><p className="text-sm">Nenhuma receita encontrada.</p></div>
      ) : (
        <>
          {/* Mobile */}
          <div className="flex flex-col gap-3 md:hidden">
            {items.map((item) => (
              <Card key={item.id}>
                <div className="flex justify-between items-start gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-gray-900 truncate">{item.descricao}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{item.tipo} &middot; {item.vencimento}</p>
                  </div>
                  <Badge status={item.status} />
                </div>
                <div className="mt-2 flex justify-between items-center">
                  <span className="text-lg font-bold text-green-700">{BRL(item.valor_liquido)}</span>
                  <span className="text-xs text-gray-400">{item.conta_nome}</span>
                </div>
                <div className="mt-3 flex gap-2 flex-wrap">
                  {item.status === 'PENDENTE' && (
                    <Button size="sm" onClick={() => marcarRecebido(item)}>Receber</Button>
                  )}
                  <Button size="sm" variant="secondary" onClick={() => openEdit(item)}>Editar</Button>
                  <Button size="sm" variant="danger" onClick={() => handleDelete(item)}>Excluir</Button>
                </div>
              </Card>
            ))}
          </div>

          {/* Desktop */}
          <div className="hidden md:block">
            <Card>
              <div className="overflow-x-auto -mx-6 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Descrição</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Tipo</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600">Valor</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Vencimento</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Status</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Conta</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {items.map((item) => (
                      <tr key={item.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-900 max-w-[200px] truncate">{item.descricao}</td>
                        <td className="px-4 py-3 text-gray-600">{item.tipo}</td>
                        <td className="px-4 py-3 text-right font-semibold text-green-700">{BRL(item.valor_liquido)}</td>
                        <td className="px-4 py-3 text-gray-600">{item.vencimento}</td>
                        <td className="px-4 py-3"><Badge status={item.status} /></td>
                        <td className="px-4 py-3 text-gray-600">{item.conta_nome}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {item.status === 'PENDENTE' && (
                              <Button size="sm" onClick={() => marcarRecebido(item)}>Receber</Button>
                            )}
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
        <Modal title={editingId ? 'Editar Receita' : 'Nova Receita'} onClose={closeModal} maxW="max-w-2xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Select label="Tipo" name="tipo" options={TIPO_RECEITA} value={form.tipo} onChange={handleChange} />
              <Select label="Conta" name="conta" options={[{ value: '', label: 'Selecione...' }, ...contasOptions]} value={form.conta} onChange={handleChange} required />
            </div>
            <Input label="Descrição" name="descricao" value={form.descricao} onChange={handleChange} />
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Input label="Valor Bruto (R$)" name="valor_bruto" type="number" step="0.01" min="0" value={form.valor_bruto} onChange={handleChange} />
              <Input label="Desconto (R$)" name="desconto" type="number" step="0.01" min="0" value={form.desconto} onChange={handleChange} />
              <Input label="Vencimento" name="vencimento" type="date" value={form.vencimento} onChange={handleChange} />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700">Observações</label>
              <textarea name="observacoes" value={form.observacoes} onChange={handleChange} rows={2}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent" />
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

const EMPTY_RECEITA = {
  tipo: 'SERVICO', descricao: '', cliente: '', categoria: '',
  valor_bruto: '', desconto: '0', conta: '', vencimento: '', observacoes: '',
}

function DespesasTab({ showToast, contasOptions }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(EMPTY_DESPESA)

  const fetch = useCallback(async () => {
    setLoading(true)
    try {
      const params = { search, page, page_size: PAGE_SIZE }
      if (statusFilter) params.status = statusFilter
      const r = await api.get('/financeiro/despesas/', { params })
      setItems(r.data.results || r.data || [])
      const count = r.data.count || (r.data.results || r.data || []).length
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
    } catch { showToast('Erro ao carregar despesas.', 'error') }
    finally { setLoading(false) }
  }, [search, statusFilter, page])

  useEffect(() => { fetch() }, [fetch])

  const handleChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }))

  const openNew = () => { setForm(EMPTY_DESPESA); setEditingId(null); setModalOpen(true) }
  const openEdit = (item) => {
    setForm({
      tipo: item.tipo || 'VARIAVEL', descricao: item.descricao || '',
      fornecedor: item.fornecedor || '', categoria: item.categoria || '',
      valor_bruto: item.valor_bruto || '', desconto: item.desconto || '0',
      conta: item.conta || '', vencimento: item.vencimento || '',
      forma_pagamento: item.forma_pagamento || '', observacoes: item.observacoes || '',
    })
    setEditingId(item.id); setModalOpen(true)
  }
  const closeModal = () => { setModalOpen(false); setEditingId(null) }

  const handleSubmit = async (e) => {
    e.preventDefault(); setSaving(true)
    try {
      const payload = stripEmptyStrings(form)
      if (editingId) {
        await api.patch(`/financeiro/despesas/${editingId}/`, payload)
        showToast('Despesa atualizada.')
      } else {
        await api.post('/financeiro/despesas/', payload)
        showToast('Despesa cadastrada.')
      }
      closeModal(); fetch()
    } catch (error) { showToast(extractErrorMessage(error, 'Erro ao salvar despesa.'), 'error') }
    finally { setSaving(false) }
  }

  const marcarPago = async (item) => {
    try {
      await api.patch(`/financeiro/despesas/${item.id}/pagar/`, {})
      showToast('Despesa marcada como paga.')
      fetch()
    } catch (error) { showToast(extractErrorMessage(error, 'Erro ao marcar pagamento.'), 'error') }
  }

  const handleDelete = async (item) => {
    if (!window.confirm(`Excluir "${item.descricao}"?`)) return
    try { await api.delete(`/financeiro/despesas/${item.id}/`); showToast('Despesa removida.'); fetch() }
    catch (error) { showToast(extractErrorMessage(error, 'Erro ao remover.'), 'error') }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-800">Contas a Pagar</h2>
        <Button onClick={openNew}>+ Nova Despesa</Button>
      </div>

      <Card>
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <Input placeholder="Buscar..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} />
          </div>
          <div className="w-full sm:w-48">
            <Select options={STATUS_DESPESA} value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }} />
          </div>
        </div>
      </Card>

      {loading ? (
        <div className="text-center py-12 text-gray-400 text-sm">Carregando...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-400"><p className="text-sm">Nenhuma despesa encontrada.</p></div>
      ) : (
        <>
          {/* Mobile */}
          <div className="flex flex-col gap-3 md:hidden">
            {items.map((item) => (
              <Card key={item.id}>
                <div className="flex justify-between items-start gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-gray-900 truncate">{item.descricao}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{item.tipo} &middot; {item.vencimento}</p>
                  </div>
                  <Badge status={item.status} />
                </div>
                <div className="mt-2 flex justify-between items-center">
                  <span className="text-lg font-bold text-red-700">{BRL(item.valor_liquido)}</span>
                  <span className="text-xs text-gray-400">{item.conta_nome}</span>
                </div>
                {item.fornecedor && <p className="text-xs text-gray-500 mt-1">{item.fornecedor}</p>}
                <div className="mt-3 flex gap-2 flex-wrap">
                  {item.status === 'PENDENTE' && (
                    <Button size="sm" onClick={() => marcarPago(item)}>Pagar</Button>
                  )}
                  <Button size="sm" variant="secondary" onClick={() => openEdit(item)}>Editar</Button>
                  <Button size="sm" variant="danger" onClick={() => handleDelete(item)}>Excluir</Button>
                </div>
              </Card>
            ))}
          </div>

          {/* Desktop */}
          <div className="hidden md:block">
            <Card>
              <div className="overflow-x-auto -mx-6 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Descrição</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Tipo</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600">Valor</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Vencimento</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Status</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Fornecedor</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {items.map((item) => (
                      <tr key={item.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-900 max-w-[200px] truncate">{item.descricao}</td>
                        <td className="px-4 py-3 text-gray-600">{item.tipo}</td>
                        <td className="px-4 py-3 text-right font-semibold text-red-700">{BRL(item.valor_liquido)}</td>
                        <td className="px-4 py-3 text-gray-600">{item.vencimento}</td>
                        <td className="px-4 py-3"><Badge status={item.status} /></td>
                        <td className="px-4 py-3 text-gray-600 max-w-[120px] truncate">{item.fornecedor || '—'}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {item.status === 'PENDENTE' && (
                              <Button size="sm" onClick={() => marcarPago(item)}>Pagar</Button>
                            )}
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
        <Modal title={editingId ? 'Editar Despesa' : 'Nova Despesa'} onClose={closeModal} maxW="max-w-2xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Select label="Tipo" name="tipo" options={TIPO_DESPESA} value={form.tipo} onChange={handleChange} />
              <Select label="Conta" name="conta" options={[{ value: '', label: 'Selecione...' }, ...contasOptions]} value={form.conta} onChange={handleChange} required />
            </div>
            <Input label="Descrição" name="descricao" value={form.descricao} onChange={handleChange} />
            <Input label="Fornecedor" name="fornecedor" value={form.fornecedor} onChange={handleChange} />
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Input label="Valor Bruto (R$)" name="valor_bruto" type="number" step="0.01" min="0" value={form.valor_bruto} onChange={handleChange} />
              <Input label="Desconto (R$)" name="desconto" type="number" step="0.01" min="0" value={form.desconto} onChange={handleChange} />
              <Input label="Vencimento" name="vencimento" type="date" value={form.vencimento} onChange={handleChange} />
            </div>
            <Select label="Forma de Pagamento" name="forma_pagamento" options={FORMA_PAGAMENTO} value={form.forma_pagamento} onChange={handleChange} />
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700">Observações</label>
              <textarea name="observacoes" value={form.observacoes} onChange={handleChange} rows={2}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent" />
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

const EMPTY_DESPESA = {
  tipo: 'VARIAVEL', descricao: '', fornecedor: '', categoria: '',
  valor_bruto: '', desconto: '0', conta: '', vencimento: '',
  forma_pagamento: '', observacoes: '',
}

function ContasTab({ showToast }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState(EMPTY_CONTA)
  const [totais, setTotais] = useState(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    try {
      const [r, t] = await Promise.all([
        api.get('/financeiro/contas/'),
        api.get('/financeiro/livro-caixa/totais/'),
      ])
      setItems(r.data.results || r.data || [])
      setTotais(t.data)
    } catch { showToast('Erro ao carregar contas.', 'error') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetch() }, [fetch])

  const handleChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }))

  const openNew = () => { setForm(EMPTY_CONTA); setEditingId(null); setModalOpen(true) }
  const openEdit = (item) => {
    setForm({
      nome: item.nome || '', tipo: item.tipo || 'CORRENTE',
      banco: item.banco || '', agencia: item.agencia || '',
      numero: item.numero || '', saldo_inicial: item.saldo_inicial || '0',
    })
    setEditingId(item.id); setModalOpen(true)
  }
  const closeModal = () => { setModalOpen(false); setEditingId(null) }

  const handleSubmit = async (e) => {
    e.preventDefault(); setSaving(true)
    try {
      const payload = stripEmptyStrings(form)
      if (editingId) {
        await api.patch(`/financeiro/contas/${editingId}/`, payload)
        showToast('Conta atualizada.')
      } else {
        await api.post('/financeiro/contas/', payload)
        showToast('Conta cadastrada.')
      }
      closeModal(); fetch()
    } catch (error) { showToast(extractErrorMessage(error, 'Erro ao salvar conta.'), 'error') }
    finally { setSaving(false) }
  }

  const handleDelete = async (item) => {
    if (!window.confirm(`Excluir a conta "${item.nome}"?`)) return
    try { await api.delete(`/financeiro/contas/${item.id}/`); showToast('Conta removida.'); fetch() }
    catch (error) { showToast(extractErrorMessage(error, 'Erro ao remover conta.'), 'error') }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-800">Contas Bancárias</h2>
        <Button onClick={openNew}>+ Nova Conta</Button>
      </div>

      {totais && (
        <div className="grid grid-cols-3 gap-3">
          <KpiCard label="Entradas" value={BRL(totais.total_entradas)} color="green" />
          <KpiCard label="Saídas" value={BRL(totais.total_saidas)} color="red" />
          <KpiCard label="Saldo Atual" value={BRL(totais.saldo_atual)} color="blue" />
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-400 text-sm">Carregando...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-400"><p className="text-sm">Nenhuma conta cadastrada.</p></div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {items.map((item) => (
            <Card key={item.id}>
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-semibold text-gray-900">{item.nome}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{item.tipo} {item.banco ? `— ${item.banco}` : ''}</p>
                </div>
              </div>
              {(item.agencia || item.numero) && (
                <p className="text-xs text-gray-400 mt-1">Ag: {item.agencia || '—'} / CC: {item.numero || '—'}</p>
              )}
              <p className="text-sm text-gray-600 mt-2">Saldo inicial: {BRL(item.saldo_inicial)}</p>
              <div className="mt-3 flex gap-2">
                <Button size="sm" variant="secondary" onClick={() => openEdit(item)}>Editar</Button>
                <Button size="sm" variant="danger" onClick={() => handleDelete(item)}>Excluir</Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {modalOpen && (
        <Modal title={editingId ? 'Editar Conta' : 'Nova Conta'} onClose={closeModal}>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label="Nome" name="nome" value={form.nome} onChange={handleChange} />
            <Select label="Tipo" name="tipo" options={TIPO_CONTA} value={form.tipo} onChange={handleChange} />
            <Input label="Banco" name="banco" value={form.banco} onChange={handleChange} />
            <div className="grid grid-cols-2 gap-4">
              <Input label="Agência" name="agencia" value={form.agencia} onChange={handleChange} />
              <Input label="Número" name="numero" value={form.numero} onChange={handleChange} />
            </div>
            <Input label="Saldo Inicial (R$)" name="saldo_inicial" type="number" step="0.01" value={form.saldo_inicial} onChange={handleChange} />
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

const EMPTY_CONTA = {
  nome: '', tipo: 'CORRENTE', banco: '', agencia: '', numero: '', saldo_inicial: '0',
}

const MESES_OPTS = [
  { value: '', label: 'Ano completo' },
  { value: '1', label: 'Janeiro' }, { value: '2', label: 'Fevereiro' },
  { value: '3', label: 'Março' }, { value: '4', label: 'Abril' },
  { value: '5', label: 'Maio' }, { value: '6', label: 'Junho' },
  { value: '7', label: 'Julho' }, { value: '8', label: 'Agosto' },
  { value: '9', label: 'Setembro' }, { value: '10', label: 'Outubro' },
  { value: '11', label: 'Novembro' }, { value: '12', label: 'Dezembro' },
]

const MESES_SHORT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

const DRE_LINHAS = [
  { key: 'receita_operacional', label: 'Receita Operacional', bold: false },
  { key: 'receita_financeira', label: 'Receita Financeira', bold: false },
  { key: 'receita_bruta', label: 'Receita Bruta', bold: true },
  { key: 'descontos', label: '(-) Descontos', bold: false, negative: true },
  { key: 'receita_liquida', label: 'Receita Líquida', bold: true },
  { key: 'despesas_fixas', label: '(-) Despesas Fixas', bold: false, negative: true },
  { key: 'despesas_variaveis', label: '(-) Despesas Variáveis', bold: false, negative: true },
  { key: 'prolabore', label: '(-) Pró-labore', bold: false, negative: true },
  { key: 'impostos', label: '(-) Impostos/DAS', bold: false, negative: true },
  { key: 'outros', label: '(-) Outros', bold: false, negative: true },
  { key: 'total_despesas', label: 'Total Despesas', bold: true, negative: true },
  { key: 'resultado', label: 'Resultado Líquido', bold: true, highlight: true },
  { key: 'ebitda', label: 'EBITDA', bold: true, highlight: true },
]

function DreTab() {
  const currentYear = new Date().getFullYear()
  const [ano, setAno] = useState(String(currentYear))
  const [mes, setMes] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const anoOpts = Array.from({ length: 4 }, (_, i) => ({
    value: String(currentYear - 2 + i), label: String(currentYear - 2 + i),
  }))

  useEffect(() => {
    setLoading(true)
    const params = { ano }
    if (mes) params.mes = mes
    api.get('/financeiro/dre/', { params })
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [ano, mes])

  if (loading) return <div className="text-center py-12 text-gray-400">Carregando...</div>
  if (!data) return <div className="text-center py-12 text-gray-400">Erro ao carregar DRE.</div>

  const singleMonth = !!mes && data.dados

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-lg font-semibold text-gray-800">Demonstrativo de Resultado (DRE)</h2>
        <div className="flex gap-2">
          <div className="w-28">
            <Select options={anoOpts} value={ano} onChange={(e) => setAno(e.target.value)} />
          </div>
          <div className="w-40">
            <Select options={MESES_OPTS} value={mes} onChange={(e) => setMes(e.target.value)} />
          </div>
        </div>
      </div>

      {singleMonth ? (
        <Card title={`DRE — ${data.dados.mes}`}>
          <div className="space-y-1">
            {DRE_LINHAS.map((l) => {
              const val = Number(data.dados[l.key] || 0)
              return (
                <div key={l.key} className={`flex justify-between py-1.5 px-2 rounded ${l.highlight ? 'bg-gray-50' : ''}`}>
                  <span className={`text-sm ${l.bold ? 'font-bold text-gray-900' : 'text-gray-600'}`}>{l.label}</span>
                  <span className={`text-sm font-mono ${l.bold ? 'font-bold' : ''} ${l.highlight ? (val >= 0 ? 'text-green-700' : 'text-red-700') : 'text-gray-800'}`}>
                    {BRL(val)}
                  </span>
                </div>
              )
            })}
          </div>

          {(data.dados.receitas_por_categoria && Object.keys(data.dados.receitas_por_categoria).length > 0) && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <p className="text-sm font-semibold text-gray-700 mb-2">Receitas por Categoria</p>
              {Object.entries(data.dados.receitas_por_categoria).map(([cat, val]) => (
                <div key={cat} className="flex justify-between py-1 px-2 text-sm">
                  <span className="text-gray-600">{cat}</span>
                  <span className="font-mono text-green-700">{BRL(val)}</span>
                </div>
              ))}
            </div>
          )}
          {(data.dados.despesas_por_categoria && Object.keys(data.dados.despesas_por_categoria).length > 0) && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <p className="text-sm font-semibold text-gray-700 mb-2">Despesas por Categoria</p>
              {Object.entries(data.dados.despesas_por_categoria).map(([cat, val]) => (
                <div key={cat} className="flex justify-between py-1 px-2 text-sm">
                  <span className="text-gray-600">{cat}</span>
                  <span className="font-mono text-red-700">{BRL(val)}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      ) : (
        <>
          {/* Mobile: single-column month cards */}
          <div className="flex flex-col gap-3 md:hidden">
            {data.meses?.filter((m) => {
              const total = DRE_LINHAS.reduce((s, l) => s + Math.abs(Number(m[l.key] || 0)), 0)
              return total > 0
            }).map((m, i) => (
              <Card key={i} title={m.mes}>
                <div className="space-y-1">
                  {DRE_LINHAS.map((l) => (
                    <div key={l.key} className={`flex justify-between py-1 ${l.highlight ? 'bg-gray-50 rounded px-1' : ''}`}>
                      <span className={`text-xs ${l.bold ? 'font-bold text-gray-900' : 'text-gray-600'}`}>{l.label}</span>
                      <span className={`text-xs font-mono ${l.bold ? 'font-bold' : ''} ${l.highlight ? (Number(m[l.key] || 0) >= 0 ? 'text-green-700' : 'text-red-700') : 'text-gray-800'}`}>
                        {BRL(m[l.key])}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>

          {/* Desktop: full table */}
          <div className="hidden md:block">
            <Card>
              <div className="overflow-x-auto -mx-6 -my-4">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="text-left px-3 py-2 font-semibold text-gray-600 sticky left-0 bg-gray-50 min-w-[160px]">Linha</th>
                      {data.meses?.map((m, i) => (
                        <th key={i} className="text-right px-2 py-2 font-semibold text-gray-600 whitespace-nowrap">{MESES_SHORT[i]}</th>
                      ))}
                      <th className="text-right px-3 py-2 font-bold text-gray-800 bg-gray-100">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {DRE_LINHAS.map((l) => (
                      <tr key={l.key} className={l.highlight ? 'bg-gray-50' : 'hover:bg-gray-50'}>
                        <td className={`px-3 py-2 sticky left-0 bg-white ${l.bold ? 'font-bold text-gray-900' : 'text-gray-600'} ${l.highlight ? '!bg-gray-50' : ''}`}>
                          {l.label}
                        </td>
                        {data.meses?.map((m, i) => {
                          const val = Number(m[l.key] || 0)
                          return (
                            <td key={i} className={`px-2 py-2 text-right font-mono ${l.bold ? 'font-bold' : ''} ${l.highlight ? (val >= 0 ? 'text-green-700' : 'text-red-700') : 'text-gray-700'}`}>
                              {BRL(val)}
                            </td>
                          )
                        })}
                        <td className={`px-3 py-2 text-right font-mono font-bold bg-gray-100 ${l.highlight ? (Number(data.totais_ano?.[l.key] || 0) >= 0 ? 'text-green-700' : 'text-red-700') : 'text-gray-800'}`}>
                          {BRL(data.totais_ano?.[l.key])}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          {data.totais_ano && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <KpiCard label="Receita Líquida (Ano)" value={BRL(data.totais_ano.receita_liquida)} color="green" />
              <KpiCard label="Total Despesas (Ano)" value={BRL(data.totais_ano.total_despesas)} color="red" />
              <KpiCard label="Resultado (Ano)" value={BRL(data.totais_ano.resultado)} color={Number(data.totais_ano.resultado) >= 0 ? 'green' : 'red'} />
              <KpiCard label="EBITDA (Ano)" value={BRL(data.totais_ano.ebitda)} color={Number(data.totais_ano.ebitda) >= 0 ? 'green' : 'red'} />
            </div>
          )}
        </>
      )}
    </div>
  )
}

function BalancoTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [dataRef, setDataRef] = useState(new Date().toISOString().split('T')[0])

  useEffect(() => {
    setLoading(true)
    api.get('/financeiro/balanco/', { params: { data: dataRef } })
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [dataRef])

  if (loading) return <div className="text-center py-12 text-gray-400">Carregando...</div>
  if (!data) return <div className="text-center py-12 text-gray-400">Erro ao carregar balanço.</div>

  const BalancoRow = ({ label, value, bold, indent }) => (
    <div className={`flex justify-between py-1.5 ${indent ? 'pl-4' : ''}`}>
      <span className={`text-sm ${bold ? 'font-bold text-gray-900' : 'text-gray-600'}`}>{label}</span>
      <span className={`text-sm font-mono ${bold ? 'font-bold text-gray-900' : 'text-gray-700'}`}>{BRL(value)}</span>
    </div>
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-lg font-semibold text-gray-800">Balanço Patrimonial</h2>
        <div className="w-40">
          <Input type="date" value={dataRef} onChange={(e) => setDataRef(e.target.value)} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card title="Ativo">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mt-1">Circulante</p>
            <BalancoRow label="Caixa e Equivalentes" value={data.ativo.circulante.caixa_equivalentes} indent />
            <BalancoRow label="Contas a Receber" value={data.ativo.circulante.contas_a_receber} indent />
            <BalancoRow label="Total Circulante" value={data.ativo.circulante.total} bold />
            <div className="border-t border-gray-200 mt-2 pt-2">
              <BalancoRow label="ATIVO TOTAL" value={data.ativo.total} bold />
            </div>
          </div>
        </Card>

        <div className="space-y-4">
          <Card title="Passivo">
            <div className="space-y-1">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mt-1">Circulante</p>
              <BalancoRow label="Contas a Pagar" value={data.passivo.circulante.contas_a_pagar} indent />
              <BalancoRow label="Total Circulante" value={data.passivo.circulante.total} bold />
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mt-2">Exigível LP</p>
              <BalancoRow label="Empréstimos" value={data.passivo.exigivel_lp.emprestimos} indent />
              <BalancoRow label="Total Exigível LP" value={data.passivo.exigivel_lp.total} bold />
              <div className="border-t border-gray-200 mt-2 pt-2">
                <BalancoRow label="PASSIVO TOTAL" value={data.passivo.total} bold />
              </div>
            </div>
          </Card>

          <Card title="Patrimônio Líquido">
            <div className="space-y-1">
              <BalancoRow label="Capital / Aportes" value={data.patrimonio_liquido.capital_aportes} indent />
              <BalancoRow label="Lucros Acumulados" value={data.patrimonio_liquido.lucros_acumulados} indent />
              <div className="border-t border-gray-200 mt-2 pt-2">
                <BalancoRow label="PL TOTAL" value={data.patrimonio_liquido.total} bold />
              </div>
            </div>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <KpiCard label="Ativo Total" value={BRL(data.total_ativo)} color="blue" />
        <KpiCard label="Passivo + PL" value={BRL(data.total_passivo_pl)} color="blue" />
        <div className={`rounded-xl p-4 ${data.equacao_ok ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          <p className="text-xs font-medium opacity-70">Equação</p>
          <p className="text-lg font-bold mt-1">{data.equacao_ok ? 'OK — Balanceado' : 'Desequilíbrio!'}</p>
        </div>
      </div>
    </div>
  )
}

function IndicadoresTab() {
  const [indicadores, setIndicadores] = useState(null)
  const [fluxo, setFluxo] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.get('/financeiro/indicadores/'),
      api.get('/financeiro/fluxo-projetado/'),
    ])
      .then(([ind, fl]) => {
        setIndicadores(ind.data)
        setFluxo(fl.data)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-center py-12 text-gray-400">Carregando...</div>
  if (!indicadores) return <div className="text-center py-12 text-gray-400">Erro ao carregar indicadores.</div>

  const DeltaArrow = ({ value }) => {
    const v = Number(value || 0)
    if (v === 0) return <span className="text-gray-400 text-xs">—</span>
    return (
      <span className={`text-xs font-semibold ${v > 0 ? 'text-green-600' : 'text-red-600'}`}>
        {v > 0 ? '▲' : '▼'} {Math.abs(v).toFixed(1)}%
      </span>
    )
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-800">Indicadores de CFO</h2>

      <Card title="Rentabilidade">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="space-y-1">
            <p className="text-xs text-gray-500">Margem Líquida</p>
            <p className="text-lg font-bold text-gray-900">{indicadores.margem_liquida}%</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-gray-500">EBITDA (mês)</p>
            <p className="text-lg font-bold text-gray-900">{BRL(indicadores.ebitda_mes)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-gray-500">vs. Mês Anterior</p>
            <DeltaArrow value={indicadores.var_mes_anterior} />
          </div>
          <div className="space-y-1">
            <p className="text-xs text-gray-500">vs. Mesmo Mês (Ano Ant.)</p>
            <DeltaArrow value={indicadores.var_ano_anterior} />
          </div>
        </div>
      </Card>

      <Card title="Operacional">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <div className="space-y-1">
            <p className="text-xs text-gray-500">Ponto de Equilíbrio</p>
            <p className="text-lg font-bold text-gray-900">{BRL(indicadores.ponto_equilibrio)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-gray-500">Ticket Médio</p>
            <p className="text-lg font-bold text-gray-900">{BRL(indicadores.ticket_medio)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-gray-500">MRR</p>
            <p className="text-lg font-bold text-gray-900">{BRL(indicadores.mrr)}</p>
          </div>
        </div>
      </Card>

      <Card title="Liquidez & Sobrevivência">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <div className="space-y-1">
            <p className="text-xs text-gray-500">Saldo Total</p>
            <p className="text-lg font-bold text-gray-900">{BRL(indicadores.saldo_total)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-gray-500">Runway</p>
            <p className={`text-lg font-bold ${Number(indicadores.runway_meses) >= 6 ? 'text-green-700' : Number(indicadores.runway_meses) >= 3 ? 'text-yellow-700' : 'text-red-700'}`}>
              {indicadores.runway_meses} meses
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-gray-500">Resultado (mês)</p>
            <p className={`text-lg font-bold ${Number(indicadores.resultado_mes) >= 0 ? 'text-green-700' : 'text-red-700'}`}>
              {BRL(indicadores.resultado_mes)}
            </p>
          </div>
        </div>
      </Card>

      {fluxo && (
        <Card title="Fluxo de Caixa Projetado (90 dias)">
          <div className="space-y-3">
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-600">Saldo Atual</span>
              <span className="font-bold text-blue-700">{BRL(fluxo.saldo_atual)}</span>
            </div>

            {fluxo.janelas?.map((j) => {
              const maxVal = Math.max(
                ...fluxo.janelas.map((w) => Math.max(Number(w.entradas_previstas), Number(w.saidas_previstas), 1))
              )
              const wEntrada = (Number(j.entradas_previstas) / maxVal) * 100
              const wSaida = (Number(j.saidas_previstas) / maxVal) * 100
              return (
                <div key={j.periodo} className="space-y-1">
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>{j.periodo} dias</span>
                    <span className={Number(j.resultado_previsto) >= 0 ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}>
                      {BRL(j.resultado_previsto)}
                    </span>
                  </div>
                  <div className="flex gap-1 h-4">
                    <div className="bg-green-400 rounded" style={{ width: `${wEntrada}%` }} title={`Entradas: ${BRL(j.entradas_previstas)}`} />
                    <div className="bg-red-400 rounded" style={{ width: `${wSaida}%` }} title={`Saídas: ${BRL(j.saidas_previstas)}`} />
                  </div>
                </div>
              )
            })}

            <div className="border-t border-gray-200 pt-2 flex justify-between items-center text-sm">
              <span className="text-gray-600 font-medium">Saldo Projetado (90 dias)</span>
              <span className={`font-bold ${Number(fluxo.saldo_projetado_90_dias) >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                {BRL(fluxo.saldo_projetado_90_dias)}
              </span>
            </div>

            <div className="flex gap-4 text-xs text-gray-500">
              <span className="flex items-center gap-1"><span className="w-2 h-2 bg-green-400 rounded-full" />Entradas</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 bg-red-400 rounded-full" />Saídas</span>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}

function LivroCaixaTab({ contasOptions }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [contaFilter, setContaFilter] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  const fetch = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page, page_size: PAGE_SIZE }
      if (contaFilter) params.conta = contaFilter
      const r = await api.get('/financeiro/livro-caixa/', { params })
      setItems(r.data.results || r.data || [])
      const count = r.data.count || (r.data.results || r.data || []).length
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
    } catch {}
    finally { setLoading(false) }
  }, [contaFilter, page])

  useEffect(() => { fetch() }, [fetch])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-800">Livro Caixa</h2>
        <div className="w-48">
          <Select options={[{ value: '', label: 'Todas as contas' }, ...contasOptions]} value={contaFilter} onChange={(e) => { setContaFilter(e.target.value); setPage(1) }} />
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400 text-sm">Carregando...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-400"><p className="text-sm">Nenhum lançamento encontrado.</p></div>
      ) : (
        <>
          {/* Mobile */}
          <div className="flex flex-col gap-3 md:hidden">
            {items.map((item) => (
              <Card key={item.id}>
                <div className="flex justify-between items-start gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-gray-900 truncate">{item.descricao}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{item.origem_label} &middot; {item.data}</p>
                  </div>
                  <span className={`text-lg font-bold ${item.tipo === 'ENTRADA' ? 'text-green-700' : 'text-red-700'}`}>
                    {item.tipo === 'ENTRADA' ? '+' : '-'}{BRL(item.valor)}
                  </span>
                </div>
                <div className="mt-2 flex justify-between text-xs text-gray-500">
                  <span>{item.conta_nome}</span>
                  <span>Saldo: {BRL(item.saldo_atual)}</span>
                </div>
                {item.estornado && <span className="text-xs text-red-500 font-medium mt-1 block">ESTORNADO</span>}
              </Card>
            ))}
          </div>

          {/* Desktop */}
          <div className="hidden md:block">
            <Card>
              <div className="overflow-x-auto -mx-6 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Data</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Descrição</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Origem</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600">Conta</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600">Valor</th>
                      <th className="text-right px-4 py-3 font-semibold text-gray-600">Saldo</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {items.map((item) => (
                      <tr key={item.id} className={`hover:bg-gray-50 ${item.estornado ? 'opacity-50 line-through' : ''}`}>
                        <td className="px-4 py-3 text-gray-600">{item.data}</td>
                        <td className="px-4 py-3 font-medium text-gray-900 max-w-[250px] truncate">{item.descricao}</td>
                        <td className="px-4 py-3 text-gray-600">{item.origem_label}</td>
                        <td className="px-4 py-3 text-gray-600">{item.conta_nome}</td>
                        <td className={`px-4 py-3 text-right font-semibold ${item.tipo === 'ENTRADA' ? 'text-green-700' : 'text-red-700'}`}>
                          {item.tipo === 'ENTRADA' ? '+' : '-'}{BRL(item.valor)}
                        </td>
                        <td className="px-4 py-3 text-right text-gray-700 font-medium">{BRL(item.saldo_atual)}</td>
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
    </div>
  )
}

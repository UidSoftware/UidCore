import { useState, useEffect, useCallback } from 'react'
import { User, Building2, Plus, Trash2 } from 'lucide-react'
import api from '../api/client.js'
import { extractErrorMessage, stripEmptyStrings } from '../utils/errors.js'
import Card from '../components/ui/Card.jsx'
import Button from '../components/ui/Button.jsx'
import Input from '../components/ui/Input.jsx'
import Select from '../components/ui/Select.jsx'
import Modal from '../components/ui/Modal.jsx'
import Pagination from '../components/ui/Pagination.jsx'

const PAGE_SIZE = 10

const UF_OPTIONS = [
  { value: '', label: 'Selecione...' },
  { value: 'AC', label: 'AC' }, { value: 'AL', label: 'AL' }, { value: 'AM', label: 'AM' },
  { value: 'AP', label: 'AP' }, { value: 'BA', label: 'BA' }, { value: 'CE', label: 'CE' },
  { value: 'DF', label: 'DF' }, { value: 'ES', label: 'ES' }, { value: 'GO', label: 'GO' },
  { value: 'MA', label: 'MA' }, { value: 'MG', label: 'MG' }, { value: 'MS', label: 'MS' },
  { value: 'MT', label: 'MT' }, { value: 'PA', label: 'PA' }, { value: 'PB', label: 'PB' },
  { value: 'PE', label: 'PE' }, { value: 'PI', label: 'PI' }, { value: 'PR', label: 'PR' },
  { value: 'RJ', label: 'RJ' }, { value: 'RN', label: 'RN' }, { value: 'RO', label: 'RO' },
  { value: 'RR', label: 'RR' }, { value: 'RS', label: 'RS' }, { value: 'SC', label: 'SC' },
  { value: 'SE', label: 'SE' }, { value: 'SP', label: 'SP' }, { value: 'TO', label: 'TO' },
]

const SEGMENTO_OPTIONS = [
  { value: '', label: 'Selecione...' },
  { value: 'COMERCIO', label: 'Comércio' },
  { value: 'SERVICOS', label: 'Serviços' },
  { value: 'INDUSTRIA', label: 'Indústria' },
  { value: 'SAUDE', label: 'Saúde' },
  { value: 'EDUCACAO', label: 'Educação' },
  { value: 'TECNOLOGIA', label: 'Tecnologia' },
  { value: 'ALIMENTACAO', label: 'Alimentação' },
  { value: 'OUTRO', label: 'Outro' },
]

const maskCPF = (v) => {
  const d = v.replace(/\D/g, '').slice(0, 11)
  if (d.length <= 3) return d
  if (d.length <= 6) return `${d.slice(0, 3)}.${d.slice(3)}`
  if (d.length <= 9) return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6)}`
  return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`
}

const maskCNPJ = (v) => {
  const d = v.replace(/\D/g, '').slice(0, 14)
  if (d.length <= 2) return d
  if (d.length <= 5) return `${d.slice(0, 2)}.${d.slice(2)}`
  if (d.length <= 8) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5)}`
  if (d.length <= 12) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8)}`
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`
}

const EMPTY_ACIONISTA = { nome: '', email: '', cpf: '', telefone: '', whatsapp: '', principal: false }

const EMPTY_FORM = {
  tipo_pessoa: 'PF',
  cpf: '',
  cnpj: '',
  nome_razao_social: '',
  telefone: '',
  email: '',
  endereco: '',
  numero: '',
  complemento: '',
  cep: '',
  cidade: '',
  estado: '',
  data_nascimento: '',
  origem: '',
  site: '',
  segmento: '',
  limite_credito: '',
  observacoes: '',
}

export default function Clientes() {
  const [clientes, setClientes] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)
  const [acionistas, setAcionistas] = useState([])

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), type === 'error' ? 7000 : 3500)
  }

  const fetchClientes = useCallback(async () => {
    setLoading(true)
    try {
      const response = await api.get('/clientes/', {
        params: { search, page, page_size: PAGE_SIZE },
      })
      setClientes(response.data.results)
      const count = response.data.count
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
    } catch {
      showToast('Erro ao carregar clientes.', 'error')
    } finally {
      setLoading(false)
    }
  }, [search, page])

  useEffect(() => {
    fetchClientes()
  }, [fetchClientes])

  const openNew = () => {
    setForm(EMPTY_FORM)
    setAcionistas([])
    setEditingId(null)
    setModalOpen(true)
  }

  const openEdit = async (cliente) => {
    setForm({
      tipo_pessoa: cliente.tipo_pessoa || 'PF',
      cpf: cliente.cpf || '',
      cnpj: cliente.cnpj || '',
      nome_razao_social: cliente.nome_razao_social || '',
      telefone: cliente.telefone || '',
      email: cliente.email || '',
      endereco: cliente.endereco || '',
      numero: cliente.numero || '',
      complemento: cliente.complemento || '',
      cep: cliente.cep || '',
      cidade: cliente.cidade || '',
      estado: cliente.estado || '',
      data_nascimento: cliente.data_nascimento || '',
      origem: cliente.origem || '',
      site: cliente.site || '',
      segmento: cliente.segmento || '',
      limite_credito: cliente.limite_credito || '',
      observacoes: cliente.observacoes || '',
    })
    setEditingId(cliente.id)
    setAcionistas([])
    setModalOpen(true)
    // Carregar acionistas em paralelo
    try {
      const r = await api.get(`/clientes/${cliente.id}/acionistas/`)
      setAcionistas(r.data.results || r.data || [])
    } catch {
      // silencioso — acionistas são opcionais
    }
  }

  const closeModal = () => {
    setModalOpen(false)
    setEditingId(null)
    setForm(EMPTY_FORM)
    setAcionistas([])
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    if (name === 'cpf') {
      setForm((prev) => ({ ...prev, cpf: maskCPF(value) }))
    } else if (name === 'cnpj') {
      setForm((prev) => ({ ...prev, cnpj: maskCNPJ(value) }))
    } else {
      setForm((prev) => ({ ...prev, [name]: value }))
    }
  }

  const handleTipoPessoa = (tipo) => {
    setForm((prev) => ({ ...prev, tipo_pessoa: tipo }))
  }

  // Acionistas
  const addAcionista = () => {
    setAcionistas((prev) => [...prev, { ...EMPTY_ACIONISTA }])
  }

  const removeAcionista = (idx) => {
    setAcionistas((prev) => prev.filter((_, i) => i !== idx))
  }

  const updateAcionista = (idx, field, value) => {
    setAcionistas((prev) =>
      prev.map((a, i) => {
        if (i !== idx) return a
        return { ...a, [field]: value }
      })
    )
  }

  const setPrincipal = (idx) => {
    setAcionistas((prev) =>
      prev.map((a, i) => ({ ...a, principal: i === idx }))
    )
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = stripEmptyStrings({
        ...form,
        // Envia cpf/cnpj no campo documento também para compatibilidade
        documento: form.tipo_pessoa === 'PF' ? form.cpf : form.cnpj,
      })
      let clienteId = editingId
      if (editingId) {
        await api.patch(`/clientes/${editingId}/`, payload)
        showToast('Cliente atualizado com sucesso.')
      } else {
        const r = await api.post('/clientes/', payload)
        clienteId = r.data.id
        showToast('Cliente cadastrado com sucesso.')
      }
      // Salvar acionistas (somente PJ)
      if (form.tipo_pessoa === 'PJ' && acionistas.length > 0 && clienteId) {
        for (const ac of acionistas) {
          if (!ac.id) {
            await api.post(`/clientes/${clienteId}/acionistas/`, stripEmptyStrings(ac)).catch(() => {})
          } else {
            await api.patch(`/clientes/${clienteId}/acionistas/${ac.id}/`, stripEmptyStrings(ac)).catch(() => {})
          }
        }
      }
      closeModal()
      fetchClientes()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao salvar cliente.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (cliente) => {
    if (!window.confirm(`Excluir o cliente "${cliente.nome_razao_social}"?`)) return
    try {
      await api.delete(`/clientes/${cliente.id}/`)
      showToast('Cliente removido.')
      fetchClientes()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao remover cliente.'), 'error')
    }
  }

  const handleSearchChange = (e) => {
    setSearch(e.target.value)
    setPage(1)
  }

  const isPF = form.tipo_pessoa === 'PF'

  return (
    <div className="space-y-4">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white whitespace-pre-line break-words ${
            toast.type === 'error' ? 'bg-red-600' : 'bg-accent-600'
          }`}
        >
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clientes</h1>
          <p className="text-sm text-gray-500 mt-0.5">Gerencie sua base de clientes</p>
        </div>
        <Button onClick={openNew}>+ Novo Cliente</Button>
      </div>

      {/* Search */}
      <Card>
        <Input
          placeholder="Buscar por nome, documento, e-mail..."
          value={search}
          onChange={handleSearchChange}
        />
      </Card>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-12 text-gray-400 text-sm">Carregando...</div>
      ) : clientes.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400">
          <span className="text-4xl">👥</span>
          <p className="text-sm">Nenhum cliente encontrado.</p>
        </div>
      ) : (
        <>
          {/* Mobile cards */}
          <div className="flex flex-col gap-3 md:hidden">
            {clientes.map((c) => (
              <Card key={c.id}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-gray-900 truncate">{c.nome_razao_social}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {c.tipo_pessoa_display || c.tipo_pessoa} &middot; {c.documento || '—'}
                    </p>
                  </div>
                  {c.segmento_display && (
                    <span className="shrink-0 text-xs bg-primary-50 text-primary-700 rounded-full px-2 py-0.5 font-medium">
                      {c.segmento_display}
                    </span>
                  )}
                </div>
                <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs text-gray-600">
                  {(c.cidade || c.estado) && (
                    <div>
                      <span className="text-gray-400">Cidade/UF</span>
                      <p className="font-medium text-gray-800">
                        {[c.cidade, c.estado].filter(Boolean).join(' / ')}
                      </p>
                    </div>
                  )}
                  {c.telefone && (
                    <div>
                      <span className="text-gray-400">Telefone</span>
                      <p className="font-medium text-gray-800">{c.telefone}</p>
                    </div>
                  )}
                  {c.email && (
                    <div className="col-span-2">
                      <span className="text-gray-400">E-mail</span>
                      <p className="font-medium text-gray-800 truncate">{c.email}</p>
                    </div>
                  )}
                </div>
                <div className="mt-3 flex gap-2">
                  <Button size="sm" variant="secondary" onClick={() => openEdit(c)}>Editar</Button>
                  <Button size="sm" variant="danger" onClick={() => handleDelete(c)}>Excluir</Button>
                </div>
              </Card>
            ))}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block">
            <Card>
              <div className="overflow-x-auto -mx-6 -my-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="text-left px-6 py-3 font-semibold text-gray-600 whitespace-nowrap">Nome</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap">Tipo</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap">Documento</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap">Segmento</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap">Cidade/UF</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap">Contato</th>
                      <th className="text-right px-6 py-3 font-semibold text-gray-600 whitespace-nowrap">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {clientes.map((c) => (
                      <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-3 font-medium text-gray-900 whitespace-nowrap max-w-[200px] truncate">
                          {c.nome_razao_social}
                        </td>
                        <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                          {c.tipo_pessoa_display || c.tipo_pessoa}
                        </td>
                        <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{c.documento || '—'}</td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          {c.segmento_display ? (
                            <span className="text-xs bg-primary-50 text-primary-700 rounded-full px-2 py-0.5 font-medium">
                              {c.segmento_display}
                            </span>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                          {[c.cidade, c.estado].filter(Boolean).join(' / ') || '—'}
                        </td>
                        <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                          <div>{c.telefone || '—'}</div>
                          {c.email && (
                            <div className="text-xs text-gray-400 truncate max-w-[160px]">{c.email}</div>
                          )}
                        </td>
                        <td className="px-6 py-3 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-2">
                            <Button size="sm" variant="secondary" onClick={() => openEdit(c)}>Editar</Button>
                            <Button size="sm" variant="danger" onClick={() => handleDelete(c)}>Excluir</Button>
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

      {/* Modal */}
      {modalOpen && (
        <Modal
          title={editingId ? 'Editar Cliente' : 'Novo Cliente'}
          onClose={closeModal}
          maxW="max-w-2xl"
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Segmented control PF/PJ */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1.5">Tipo de Pessoa</label>
              <div className="flex rounded-lg border border-gray-300 overflow-hidden w-fit">
                <button
                  type="button"
                  onClick={() => handleTipoPessoa('PF')}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors ${
                    isPF
                      ? 'bg-primary-600 text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <User size={16} />
                  Pessoa Física
                </button>
                <button
                  type="button"
                  onClick={() => handleTipoPessoa('PJ')}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-l border-gray-300 ${
                    !isPF
                      ? 'bg-primary-600 text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <Building2 size={16} />
                  Pessoa Jurídica
                </button>
              </div>
            </div>

            {/* Documento */}
            {isPF ? (
              <Input
                label="CPF"
                name="cpf"
                value={form.cpf}
                onChange={handleChange}
                placeholder="000.000.000-00"
              />
            ) : (
              <Input
                label="CNPJ"
                name="cnpj"
                value={form.cnpj}
                onChange={handleChange}
                placeholder="00.000.000/0000-00"
              />
            )}

            {/* Card acionistas (somente PJ) */}
            {!isPF && (
              <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-700">Socios / Acionistas</h3>
                  <button
                    type="button"
                    onClick={addAcionista}
                    className="flex items-center gap-1 text-xs text-primary-600 font-medium hover:text-primary-800 transition-colors"
                  >
                    <Plus size={14} />
                    Adicionar Socio
                  </button>
                </div>
                {acionistas.length === 0 && (
                  <p className="text-xs text-gray-400">Nenhum socio adicionado.</p>
                )}
                <div className="space-y-3">
                  {acionistas.map((ac, idx) => (
                    <div key={idx} className="bg-white rounded-lg border border-gray-200 p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
                          <input
                            type="radio"
                            name="acionista_principal"
                            checked={ac.principal}
                            onChange={() => setPrincipal(idx)}
                            className="accent-primary-600"
                          />
                          Principal
                        </label>
                        <button
                          type="button"
                          onClick={() => removeAcionista(idx)}
                          className="text-red-400 hover:text-red-600 transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <Input
                          label="Nome"
                          value={ac.nome}
                          onChange={(e) => updateAcionista(idx, 'nome', e.target.value)}
                          placeholder="Nome completo"
                        />
                        <Input
                          label="E-mail"
                          type="email"
                          value={ac.email}
                          onChange={(e) => updateAcionista(idx, 'email', e.target.value)}
                          placeholder="email@exemplo.com"
                        />
                        <Input
                          label="CPF"
                          value={ac.cpf}
                          onChange={(e) => updateAcionista(idx, 'cpf', maskCPF(e.target.value))}
                          placeholder="000.000.000-00"
                        />
                        <Input
                          label="Telefone"
                          value={ac.telefone}
                          onChange={(e) => updateAcionista(idx, 'telefone', e.target.value)}
                          placeholder="(11) 99999-0000"
                        />
                        <Input
                          label="WhatsApp"
                          value={ac.whatsapp}
                          onChange={(e) => updateAcionista(idx, 'whatsapp', e.target.value)}
                          placeholder="(11) 99999-0000"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Input
              label={isPF ? 'Nome Completo' : 'Razao Social'}
              name="nome_razao_social"
              value={form.nome_razao_social}
              onChange={handleChange}
              placeholder={isPF ? 'Nome completo' : 'Razao social da empresa'}
              required
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Telefone"
                name="telefone"
                value={form.telefone}
                onChange={handleChange}
                placeholder="(11) 99999-0000"
              />
              <Input
                label="E-mail (login)"
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                placeholder="email@exemplo.com"
                required
              />
            </div>

            {/* Logradouro completo */}
            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-2">
                <Input
                  label="Logradouro"
                  name="endereco"
                  value={form.endereco}
                  onChange={handleChange}
                  placeholder="Rua, Avenida..."
                />
              </div>
              <Input
                label="Numero"
                name="numero"
                value={form.numero}
                onChange={handleChange}
                placeholder="123"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Complemento"
                name="complemento"
                value={form.complemento}
                onChange={handleChange}
                placeholder="Apto, sala..."
              />
              <Input
                label="CEP"
                name="cep"
                value={form.cep}
                onChange={handleChange}
                placeholder="00000-000"
              />
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div className="col-span-2 sm:col-span-2">
                <Input
                  label="Cidade"
                  name="cidade"
                  value={form.cidade}
                  onChange={handleChange}
                  placeholder="Sao Paulo"
                />
              </div>
              <Select
                label="UF"
                name="estado"
                options={UF_OPTIONS}
                value={form.estado}
                onChange={handleChange}
              />
            </div>

            {isPF ? (
              <>
                <Input
                  label="Data de Nascimento"
                  name="data_nascimento"
                  type="date"
                  value={form.data_nascimento}
                  onChange={handleChange}
                />
                <Select
                  label="Segmento"
                  name="segmento"
                  options={SEGMENTO_OPTIONS}
                  value={form.segmento}
                  onChange={handleChange}
                />
              </>
            ) : (
              <>
                <Input
                  label="Origem (como conheceu a empresa)"
                  name="origem"
                  value={form.origem}
                  onChange={handleChange}
                  placeholder="Ex.: Indicacao, Google..."
                />
                <Input
                  label="Site"
                  name="site"
                  type="url"
                  value={form.site}
                  onChange={handleChange}
                  placeholder="https://www.empresa.com.br"
                />
                <Select
                  label="Segmento"
                  name="segmento"
                  options={SEGMENTO_OPTIONS}
                  value={form.segmento}
                  onChange={handleChange}
                />
              </>
            )}

            <Input
              label="Limite de Credito (R$)"
              name="limite_credito"
              type="number"
              step="0.01"
              min="0"
              value={form.limite_credito}
              onChange={handleChange}
              placeholder="0,00"
            />

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700">Observacoes</label>
              <textarea
                name="observacoes"
                value={form.observacoes}
                onChange={handleChange}
                rows={3}
                placeholder="Informacoes adicionais..."
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors duration-150"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={closeModal}>
                Cancelar
              </Button>
              <Button type="submit" loading={saving}>
                {editingId ? 'Salvar Alteracoes' : 'Cadastrar Cliente'}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

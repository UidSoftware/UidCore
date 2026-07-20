import { useState, useEffect, useCallback } from 'react'
import api from '../api/client.js'
import Card from '../components/ui/Card.jsx'
import Button from '../components/ui/Button.jsx'
import Input from '../components/ui/Input.jsx'
import Select from '../components/ui/Select.jsx'
import Modal from '../components/ui/Modal.jsx'
import Pagination from '../components/ui/Pagination.jsx'

const PAGE_SIZE = 10

const UF_OPTIONS = [
  { value: '', label: 'Selecione...' },
  { value: 'AC', label: 'AC' },
  { value: 'AL', label: 'AL' },
  { value: 'AM', label: 'AM' },
  { value: 'AP', label: 'AP' },
  { value: 'BA', label: 'BA' },
  { value: 'CE', label: 'CE' },
  { value: 'DF', label: 'DF' },
  { value: 'ES', label: 'ES' },
  { value: 'GO', label: 'GO' },
  { value: 'MA', label: 'MA' },
  { value: 'MG', label: 'MG' },
  { value: 'MS', label: 'MS' },
  { value: 'MT', label: 'MT' },
  { value: 'PA', label: 'PA' },
  { value: 'PB', label: 'PB' },
  { value: 'PE', label: 'PE' },
  { value: 'PI', label: 'PI' },
  { value: 'PR', label: 'PR' },
  { value: 'RJ', label: 'RJ' },
  { value: 'RN', label: 'RN' },
  { value: 'RO', label: 'RO' },
  { value: 'RR', label: 'RR' },
  { value: 'RS', label: 'RS' },
  { value: 'SC', label: 'SC' },
  { value: 'SE', label: 'SE' },
  { value: 'SP', label: 'SP' },
  { value: 'TO', label: 'TO' },
]

const TIPO_PESSOA_OPTIONS = [
  { value: 'PF', label: 'Pessoa Física' },
  { value: 'PJ', label: 'Pessoa Jurídica' },
]

const CATEGORIA_OPTIONS = [
  { value: '', label: 'Selecione...' },
  { value: 'MATERIA_PRIMA', label: 'Matéria-Prima' },
  { value: 'SERVICOS', label: 'Serviços' },
  { value: 'TECNOLOGIA', label: 'Tecnologia' },
  { value: 'LOGISTICA', label: 'Logística' },
  { value: 'MANUTENCAO', label: 'Manutenção' },
  { value: 'ESCRITORIO', label: 'Escritório' },
  { value: 'MARKETING', label: 'Marketing' },
  { value: 'OUTRO', label: 'Outro' },
]

const EMPTY_FORM = {
  tipo_pessoa: 'PJ',
  documento: '',
  nome_razao_social: '',
  inscricao_estadual: '',
  telefone: '',
  email: '',
  website: '',
  contato_nome: '',
  contato_telefone: '',
  endereco: '',
  cidade: '',
  estado: '',
  cep: '',
  categoria: '',
  observacoes: '',
}

export default function Fornecedores() {
  const [fornecedores, setFornecedores] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  const fetchFornecedores = useCallback(async () => {
    setLoading(true)
    try {
      const response = await api.get('/fornecedores/', {
        params: { search, page, page_size: PAGE_SIZE },
      })
      setFornecedores(response.data.results)
      const count = response.data.count
      setTotalPages(Math.max(1, Math.ceil(count / PAGE_SIZE)))
    } catch {
      showToast('Erro ao carregar fornecedores.', 'error')
    } finally {
      setLoading(false)
    }
  }, [search, page])

  useEffect(() => {
    fetchFornecedores()
  }, [fetchFornecedores])

  const openNew = () => {
    setForm(EMPTY_FORM)
    setEditingId(null)
    setModalOpen(true)
  }

  const openEdit = (fornecedor) => {
    setForm({
      tipo_pessoa: fornecedor.tipo_pessoa || 'PJ',
      documento: fornecedor.documento || '',
      nome_razao_social: fornecedor.nome_razao_social || '',
      inscricao_estadual: fornecedor.inscricao_estadual || '',
      telefone: fornecedor.telefone || '',
      email: fornecedor.email || '',
      website: fornecedor.website || '',
      contato_nome: fornecedor.contato_nome || '',
      contato_telefone: fornecedor.contato_telefone || '',
      endereco: fornecedor.endereco || '',
      cidade: fornecedor.cidade || '',
      estado: fornecedor.estado || '',
      cep: fornecedor.cep || '',
      categoria: fornecedor.categoria || '',
      observacoes: fornecedor.observacoes || '',
    })
    setEditingId(fornecedor.id)
    setModalOpen(true)
  }

  const closeModal = () => {
    setModalOpen(false)
    setEditingId(null)
    setForm(EMPTY_FORM)
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (editingId) {
        await api.patch(`/fornecedores/${editingId}/`, form)
        showToast('Fornecedor atualizado com sucesso.')
      } else {
        await api.post('/fornecedores/', form)
        showToast('Fornecedor cadastrado com sucesso.')
      }
      closeModal()
      fetchFornecedores()
    } catch {
      showToast('Erro ao salvar fornecedor.', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (fornecedor) => {
    if (!window.confirm(`Excluir o fornecedor "${fornecedor.nome_razao_social}"?`)) return
    try {
      await api.delete(`/fornecedores/${fornecedor.id}/`)
      showToast('Fornecedor removido.')
      fetchFornecedores()
    } catch {
      showToast('Erro ao remover fornecedor.', 'error')
    }
  }

  const handleSearchChange = (e) => {
    setSearch(e.target.value)
    setPage(1)
  }

  return (
    <div className="space-y-4">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white ${
            toast.type === 'error' ? 'bg-red-600' : 'bg-accent-600'
          }`}
        >
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Fornecedores</h1>
          <p className="text-sm text-gray-500 mt-0.5">Gerencie sua base de fornecedores</p>
        </div>
        <Button onClick={openNew}>+ Novo Fornecedor</Button>
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
      ) : fornecedores.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400">
          <span className="text-4xl">🏭</span>
          <p className="text-sm">Nenhum fornecedor encontrado.</p>
        </div>
      ) : (
        <>
          {/* Mobile cards */}
          <div className="flex flex-col gap-3 md:hidden">
            {fornecedores.map((f) => (
              <Card key={f.id}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-gray-900 truncate">{f.nome_razao_social}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {f.tipo_pessoa_display || f.tipo_pessoa} &middot; {f.documento || '—'}
                    </p>
                  </div>
                  {f.categoria_display && (
                    <span className="shrink-0 text-xs bg-primary-50 text-primary-700 rounded-full px-2 py-0.5 font-medium">
                      {f.categoria_display}
                    </span>
                  )}
                </div>
                <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs text-gray-600">
                  {(f.cidade || f.estado) && (
                    <div>
                      <span className="text-gray-400">Cidade/UF</span>
                      <p className="font-medium text-gray-800">
                        {[f.cidade, f.estado].filter(Boolean).join(' / ')}
                      </p>
                    </div>
                  )}
                  {f.telefone && (
                    <div>
                      <span className="text-gray-400">Telefone</span>
                      <p className="font-medium text-gray-800">{f.telefone}</p>
                    </div>
                  )}
                  {f.contato_nome && (
                    <div>
                      <span className="text-gray-400">Contato</span>
                      <p className="font-medium text-gray-800">{f.contato_nome}</p>
                    </div>
                  )}
                  {f.email && (
                    <div className="col-span-2">
                      <span className="text-gray-400">E-mail</span>
                      <p className="font-medium text-gray-800 truncate">{f.email}</p>
                    </div>
                  )}
                  {f.website && (
                    <div className="col-span-2">
                      <span className="text-gray-400">Website</span>
                      <p className="font-medium text-gray-800 truncate">{f.website}</p>
                    </div>
                  )}
                </div>
                <div className="mt-3 flex gap-2">
                  <Button size="sm" variant="secondary" onClick={() => openEdit(f)}>
                    Editar
                  </Button>
                  <Button size="sm" variant="danger" onClick={() => handleDelete(f)}>
                    Excluir
                  </Button>
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
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap">Categoria</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap">Cidade/UF</th>
                      <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap">Contato</th>
                      <th className="text-right px-6 py-3 font-semibold text-gray-600 whitespace-nowrap">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {fornecedores.map((f) => (
                      <tr key={f.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-3 font-medium text-gray-900 whitespace-nowrap max-w-[200px] truncate">
                          {f.nome_razao_social}
                        </td>
                        <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                          {f.tipo_pessoa_display || f.tipo_pessoa}
                        </td>
                        <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{f.documento || '—'}</td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          {f.categoria_display ? (
                            <span className="text-xs bg-primary-50 text-primary-700 rounded-full px-2 py-0.5 font-medium">
                              {f.categoria_display}
                            </span>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                          {[f.cidade, f.estado].filter(Boolean).join(' / ') || '—'}
                        </td>
                        <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                          <div>{f.contato_nome || f.telefone || '—'}</div>
                          {f.email && (
                            <div className="text-xs text-gray-400 truncate max-w-[160px]">{f.email}</div>
                          )}
                        </td>
                        <td className="px-6 py-3 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-2">
                            <Button size="sm" variant="secondary" onClick={() => openEdit(f)}>
                              Editar
                            </Button>
                            <Button size="sm" variant="danger" onClick={() => handleDelete(f)}>
                              Excluir
                            </Button>
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
          title={editingId ? 'Editar Fornecedor' : 'Novo Fornecedor'}
          onClose={closeModal}
          maxW="max-w-2xl"
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Select
                label="Tipo de Pessoa"
                name="tipo_pessoa"
                options={TIPO_PESSOA_OPTIONS}
                value={form.tipo_pessoa}
                onChange={handleChange}
              />
              <Input
                label="CPF / CNPJ"
                name="documento"
                value={form.documento}
                onChange={handleChange}
                placeholder="00.000.000/0001-00"
              />
            </div>

            <Input
              label="Nome / Razão Social"
              name="nome_razao_social"
              value={form.nome_razao_social}
              onChange={handleChange}
              placeholder="Nome ou razão social do fornecedor"
              required
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Inscrição Estadual"
                name="inscricao_estadual"
                value={form.inscricao_estadual}
                onChange={handleChange}
                placeholder="000.000.000.000"
              />
              <Select
                label="Categoria"
                name="categoria"
                options={CATEGORIA_OPTIONS}
                value={form.categoria}
                onChange={handleChange}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Telefone"
                name="telefone"
                value={form.telefone}
                onChange={handleChange}
                placeholder="(11) 99999-0000"
              />
              <Input
                label="E-mail"
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                placeholder="email@fornecedor.com"
              />
            </div>

            <Input
              label="Website"
              name="website"
              type="url"
              value={form.website}
              onChange={handleChange}
              placeholder="https://www.fornecedor.com.br"
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Nome do Contato"
                name="contato_nome"
                value={form.contato_nome}
                onChange={handleChange}
                placeholder="Nome do responsável"
              />
              <Input
                label="Telefone do Contato"
                name="contato_telefone"
                value={form.contato_telefone}
                onChange={handleChange}
                placeholder="(11) 99999-0000"
              />
            </div>

            <Input
              label="Endereço"
              name="endereco"
              value={form.endereco}
              onChange={handleChange}
              placeholder="Rua, número, complemento"
            />

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div className="col-span-2 sm:col-span-1">
                <Input
                  label="CEP"
                  name="cep"
                  value={form.cep}
                  onChange={handleChange}
                  placeholder="00000-000"
                />
              </div>
              <Input
                label="Cidade"
                name="cidade"
                value={form.cidade}
                onChange={handleChange}
                placeholder="São Paulo"
              />
              <Select
                label="UF"
                name="estado"
                options={UF_OPTIONS}
                value={form.estado}
                onChange={handleChange}
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-700">Observações</label>
              <textarea
                name="observacoes"
                value={form.observacoes}
                onChange={handleChange}
                rows={3}
                placeholder="Informações adicionais sobre o fornecedor..."
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors duration-150"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={closeModal}>
                Cancelar
              </Button>
              <Button type="submit" loading={saving}>
                {editingId ? 'Salvar Alterações' : 'Cadastrar Fornecedor'}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

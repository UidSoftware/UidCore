import { useState, useEffect, useCallback } from 'react'
import api from '../../api/client.js'
import { extractErrorMessage, stripEmptyStrings } from '../../utils/errors.js'
import Card from './Card.jsx'
import Button from './Button.jsx'
import Input from './Input.jsx'
import Select from './Select.jsx'
import Modal from './Modal.jsx'
import Pagination from './Pagination.jsx'

const PAGE_SIZE = 10

function fieldValue(item, field) {
  if (field.type === 'file') return ''
  const raw = item[field.name]
  if (raw === null || raw === undefined) return ''
  if (field.type === 'datetime-local' && raw) return raw.slice(0, 16)
  return raw
}

/**
 * CRUD genérico reaproveitado pelos módulos Fase E (vendas, pagamentos,
 * administrativo, rh, agendamento, portal) — mesmo padrão do Clientes.jsx,
 * parametrizado por schema em vez de repetido 15x quase igual.
 */
export default function ResourceCrud({
  resource,
  title,
  createLabel,
  emptyIcon = '📋',
  emptyText = 'Nenhum registro encontrado.',
  columns,
  fields,
  emptyForm,
  titleField,
  deleteConfirm,
  rowActions = [],
  deleteLabel = 'Excluir',
  onBeforeSubmit,
}) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)
  const [remoteOptions, setRemoteOptions] = useState({})

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), type === 'error' ? 7000 : 3500)
  }

  const fetchItems = useCallback(async () => {
    setLoading(true)
    try {
      const response = await api.get(`/${resource}/`, { params: { page, page_size: PAGE_SIZE } })
      setItems(response.data.results)
      setTotalPages(Math.max(1, Math.ceil(response.data.count / PAGE_SIZE)))
    } catch {
      showToast('Erro ao carregar dados.', 'error')
    } finally {
      setLoading(false)
    }
  }, [resource, page])

  useEffect(() => {
    fetchItems()
  }, [fetchItems])

  useEffect(() => {
    const remoteFields = fields.filter((f) => f.type === 'select-remote')
    remoteFields.forEach(async (f) => {
      try {
        const response = await api.get(`/${f.endpoint}/`, { params: { page_size: 200 } })
        setRemoteOptions((prev) => ({ ...prev, [f.name]: response.data.results }))
      } catch {
        setRemoteOptions((prev) => ({ ...prev, [f.name]: [] }))
      }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resource])

  const openNew = () => {
    setForm(emptyForm)
    setEditingId(null)
    setModalOpen(true)
  }

  const openEdit = (item) => {
    const next = {}
    fields.forEach((f) => {
      next[f.name] = fieldValue(item, f)
    })
    setForm(next)
    setEditingId(item.id)
    setModalOpen(true)
  }

  const closeModal = () => {
    setModalOpen(false)
    setEditingId(null)
    setForm(emptyForm)
  }

  const hasFileField = fields.some((f) => f.type === 'file')

  const handleChange = (e) => {
    const { name, value, files } = e.target
    if (files) {
      setForm((prev) => ({ ...prev, [name]: files[0] }))
      return
    }
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const buildPayload = () => {
    if (!hasFileField) return stripEmptyStrings(form)
    const data = new FormData()
    Object.entries(form).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') data.append(key, value)
    })
    return data
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (onBeforeSubmit) {
      const result = onBeforeSubmit(form, editingId)
      if (result === false) return
      if (typeof result === 'string') {
        showToast(result, 'error')
        return
      }
    }
    setSaving(true)
    try {
      const payload = buildPayload()
      const config = hasFileField ? { headers: { 'Content-Type': 'multipart/form-data' } } : undefined
      if (editingId) {
        await api.patch(`/${resource}/${editingId}/`, payload, config)
        showToast('Registro atualizado com sucesso.')
      } else {
        await api.post(`/${resource}/`, payload, config)
        showToast('Registro criado com sucesso.')
      }
      closeModal()
      fetchItems()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao salvar.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (item) => {
    const label = titleField ? item[titleField] : `#${item.id}`
    const msg = deleteConfirm ? deleteConfirm(item) : `${deleteLabel} "${label}"?`
    if (!window.confirm(msg)) return
    try {
      await api.delete(`/${resource}/${item.id}/`)
      showToast('Registro removido.')
      fetchItems()
    } catch (error) {
      showToast(extractErrorMessage(error, 'Erro ao remover registro.'), 'error')
    }
  }

  const handleRowAction = async (action, item) => {
    try {
      await action.onClick(item)
      if (action.successMessage) showToast(action.successMessage)
      if (action.refresh !== false) fetchItems()
    } catch (error) {
      showToast(extractErrorMessage(error, action.errorMessage || 'Erro ao executar ação.'), 'error')
    }
  }

  const renderCell = (item, col) => {
    const value = item[col.key]
    if (col.boolean) {
      return value ? (
        <span className="text-xs bg-green-50 text-green-700 rounded-full px-2 py-0.5 font-medium dark:bg-emerald-950/40 dark:text-emerald-300">Sim</span>
      ) : (
        <span className="text-xs bg-gray-100 text-gray-500 rounded-full px-2 py-0.5 font-medium dark:bg-navy-700 dark:text-slate-500">Não</span>
      )
    }
    if (value === null || value === undefined || value === '') return <span className="text-gray-400 dark:text-slate-500">—</span>
    if (col.money) return Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    if (col.date) return new Date(value).toLocaleDateString('pt-BR')
    if (col.datetime) return new Date(value).toLocaleString('pt-BR')
    if (col.badge) {
      return (
        <span className="text-xs bg-primary-50 text-primary-700 rounded-full px-2 py-0.5 font-medium dark:bg-violet-900/30 dark:text-violet-300">
          {value}
        </span>
      )
    }
    return String(value)
  }

  const renderField = (f) => {
    const commonProps = {
      key: f.name,
      label: f.label,
      name: f.name,
      value: form[f.name] ?? '',
      onChange: handleChange,
      required: f.required,
    }
    if (f.type === 'divider') {
      return <div key={f.name} className="sm:col-span-2 pt-2 mt-2 border-t border-gray-100 dark:border-navy-700" />
    }
    if (f.type === 'checkbox') {
      return (
        <div key={f.name} className={`flex items-center gap-2 pt-6 ${f.colSpan2 ? 'sm:col-span-2' : ''}`}>
          <input
            id={f.name}
            type="checkbox"
            name={f.name}
            checked={!!form[f.name]}
            onChange={(e) => {
              const checked = e.target.checked
              setForm((prev) => {
                const next = { ...prev, [f.name]: checked }
                return f.onToggle ? f.onToggle(checked, next) : next
              })
            }}
            className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-navy-500 dark:bg-navy-800 dark:text-violet-600 dark:focus:ring-violet-500"
          />
          <label htmlFor={f.name} className="text-sm font-medium text-gray-700 dark:text-slate-300">{f.label}</label>
        </div>
      )
    }
    if (f.type === 'file') {
      return (
        <div key={f.name} className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700 dark:text-slate-300">{f.label}</label>
          <input
            type="file"
            name={f.name}
            onChange={handleChange}
            required={f.required && !editingId}
            className="w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-primary-50 file:text-primary-700 file:text-sm file:font-medium hover:file:bg-primary-100 dark:text-slate-400 dark:file:bg-violet-900/30 dark:file:text-violet-300 dark:hover:file:bg-violet-900/50"
          />
          {editingId && <p className="text-xs text-gray-400 dark:text-slate-500">Deixe em branco para manter o arquivo atual.</p>}
        </div>
      )
    }
    if (f.type === 'select') {
      return <Select {...commonProps} options={f.options} />
    }
    if (f.type === 'select-remote') {
      const opts = [
        { value: '', label: 'Selecione...' },
        ...(remoteOptions[f.name] || []).map((o) => ({
          value: o.id,
          label: o[f.labelField] ?? o.id,
        })),
      ]
      return <Select {...commonProps} options={opts} />
    }
    if (f.type === 'textarea') {
      return (
        <div key={f.name} className="flex flex-col gap-1 sm:col-span-2">
          <label className="text-sm font-medium text-gray-700 dark:text-slate-300">{f.label}</label>
          <textarea
            name={f.name}
            value={form[f.name] ?? ''}
            onChange={handleChange}
            rows={3}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500 transition-colors duration-150"
          />
        </div>
      )
    }
    return (
      <div key={f.name} className={f.colSpan2 ? 'sm:col-span-2' : undefined}>
        <Input
          {...commonProps}
          key={undefined}
          type={f.type || 'text'}
          step={f.step}
          min={f.min}
          placeholder={f.placeholder}
        />
        {f.helpText && (
          <p className="text-xs text-gray-400 mt-1 dark:text-slate-500">
            {typeof f.helpText === 'function' ? f.helpText(!!editingId) : f.helpText}
          </p>
        )}
      </div>
    )
  }

  const visibleFields = fields.filter((f) => {
    if (f.hideOnEdit && editingId) return false
    if (f.showIf && !f.showIf(form)) return false
    return true
  })

  return (
    <div className="space-y-4">
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white whitespace-pre-line break-words ${
            toast.type === 'error' ? 'bg-red-600' : 'bg-accent-600'
          }`}
        >
          {toast.msg}
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100">{title}</h2>
        <Button onClick={openNew}>{createLabel}</Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12 text-gray-400 dark:text-slate-500 text-sm">Carregando...</div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400 dark:text-slate-500">
          <span className="text-4xl">{emptyIcon}</span>
          <p className="text-sm">{emptyText}</p>
        </div>
      ) : (
        <>
          <Card>
            <div className="overflow-x-auto -mx-6 -my-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200 dark:bg-navy-900 dark:border-navy-600">
                    {columns.map((col) => (
                      <th key={col.key} className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap first:px-6 dark:text-slate-400">
                        {col.label}
                      </th>
                    ))}
                    <th className="text-right px-6 py-3 font-semibold text-gray-600 whitespace-nowrap dark:text-slate-400">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-navy-700">
                  {items.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-navy-700/60 transition-colors">
                      {columns.map((col) => (
                        <td key={col.key} className="px-4 py-3 text-gray-600 whitespace-nowrap first:px-6 first:font-medium first:text-gray-900 dark:text-slate-400 dark:first:text-slate-100">
                          {renderCell(item, col)}
                        </td>
                      ))}
                      <td className="px-6 py-3 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2">
                          <Button size="sm" variant="secondary" onClick={() => openEdit(item)}>
                            Editar
                          </Button>
                          {rowActions
                            .filter((action) => !action.showIf || action.showIf(item))
                            .map((action, idx) => {
                              const Icon = action.icon
                              return (
                                <Button
                                  key={`${action.label}-${idx}`}
                                  size="sm"
                                  variant={action.variant || 'secondary'}
                                  onClick={() => handleRowAction(action, item)}
                                >
                                  {Icon && <Icon size={14} />}
                                  {action.label}
                                </Button>
                              )
                            })}
                          <Button size="sm" variant="danger" onClick={() => handleDelete(item)}>
                            {deleteLabel}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}

      {modalOpen && (
        <Modal title={editingId ? `Editar ${title}` : createLabel} onClose={closeModal} maxW="max-w-2xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {visibleFields.map((f) => renderField(f))}
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={closeModal}>
                Cancelar
              </Button>
              <Button type="submit" loading={saving}>
                {editingId ? 'Salvar Alterações' : 'Criar'}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

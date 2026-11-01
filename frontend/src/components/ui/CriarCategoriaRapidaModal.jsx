import { useState } from 'react'
import api from '../../api/client.js'
import { extractErrorMessage } from '../../utils/errors.js'
import Modal from './Modal.jsx'
import Input from './Input.jsx'
import Button from './Button.jsx'

/**
 * Atalho "+ Nova categoria" reaproveitado em 3 forms (Plano, Receita,
 * Despesa — Manutencao 88). Cria uma Categoria sem navegar para fora do
 * form atual: modal pequeno, so pede o nome, tipo vem fixo da prop (nunca
 * editavel pelo usuario aqui — quem decide o tipo e o form de origem).
 *
 * Props:
 * - tipo: 'ENTRADA' | 'SAIDA' (pre-fixado pelo form de origem)
 * - onCreated(categoriaCriada): chamado com o objeto completo no sucesso
 * - onClose(): fecha o modal (sucesso ou cancelamento)
 * - showToast(msg, type): opcional — reaproveita o toast do form-pai
 */
export default function CriarCategoriaRapidaModal({ tipo, onCreated, onClose, showToast }) {
  const [nome, setNome] = useState('')
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!nome.trim()) return
    setSaving(true)
    try {
      const { data } = await api.post('/financeiro/categorias/', { nome: nome.trim(), tipo })
      showToast?.('Categoria criada.')
      onCreated?.(data)
      onClose?.()
    } catch (error) {
      showToast?.(extractErrorMessage(error, 'Erro ao criar categoria.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal title="Nova Categoria" onClose={onClose} maxW="max-w-sm">
      <form onSubmit={handleSubmit} className="space-y-4">
        <p className="text-xs text-gray-400 dark:text-slate-500">
          Tipo: {tipo === 'ENTRADA' ? 'Entrada' : 'Saída'}
        </p>
        <Input label="Nome" name="nome" value={nome} onChange={(e) => setNome(e.target.value)} autoFocus />
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button type="submit" loading={saving} disabled={!nome.trim()}>Criar</Button>
        </div>
      </form>
    </Modal>
  )
}

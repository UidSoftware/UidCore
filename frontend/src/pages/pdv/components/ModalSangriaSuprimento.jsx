import { useState } from 'react'
import { ArrowDownCircle, ArrowUpCircle } from 'lucide-react'
import Modal from '../../../components/ui/Modal.jsx'
import Button from '../../../components/ui/Button.jsx'
import api from '../../../api/client.js'
import { extractErrorMessage } from '../../../utils/errors.js'

/**
 * Modal de Sangria / Suprimento (RF-10).
 * Props:
 *   sessaoId   — ID da sessão de caixa ativa
 *   onClose()  — fecha o modal
 *   onSucesso(movimento) — callback após criar com sucesso
 */
export default function ModalSangriaSuprimento({ sessaoId, onClose, onSucesso }) {
  const [tipo, setTipo] = useState('SANGRIA')
  const [valor, setValor] = useState('')
  const [motivo, setMotivo] = useState('')
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  const validar = () => {
    const e = {}
    if (!valor || parseFloat(valor) <= 0) e.valor = 'Informe um valor maior que zero.'
    if (!motivo.trim()) e.motivo = 'Motivo é obrigatório.'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validar()) return
    setSaving(true)
    try {
      const { data } = await api.post(`/pdv/sessoes/${sessaoId}/movimento/`, {
        tipo,
        valor,
        motivo: motivo.trim(),
      })
      onSucesso(data)
    } catch (err) {
      setErrors({ _geral: extractErrorMessage(err, 'Erro ao registrar movimento.') })
    } finally {
      setSaving(false)
    }
  }

  const tipoSangria = tipo === 'SANGRIA'

  return (
    <Modal title="Sangria / Suprimento" onClose={onClose} maxW="max-w-md">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Toggle tipo */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Tipo</label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setTipo('SANGRIA')}
              className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
                tipoSangria
                  ? 'bg-red-50 border-red-300 text-red-700'
                  : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
              }`}
            >
              <ArrowDownCircle size={16} />
              Sangria
            </button>
            <button
              type="button"
              onClick={() => setTipo('SUPRIMENTO')}
              className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
                !tipoSangria
                  ? 'bg-green-50 border-green-300 text-green-700'
                  : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
              }`}
            >
              <ArrowUpCircle size={16} />
              Suprimento
            </button>
          </div>
        </div>

        {/* Valor */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Valor <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            placeholder="0,00"
            className={`w-full rounded-lg border px-3 py-2 text-sm text-right font-mono focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors ${
              errors.valor ? 'border-red-500 bg-red-50' : 'border-gray-300 bg-white'
            }`}
          />
          {errors.valor && <p className="mt-1 text-xs text-red-600">{errors.valor}</p>}
        </div>

        {/* Motivo */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Motivo <span className="text-red-500">*</span>
          </label>
          <textarea
            rows={2}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            placeholder="Descreva o motivo..."
            className={`w-full rounded-lg border px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors resize-none ${
              errors.motivo ? 'border-red-500 bg-red-50' : 'border-gray-300 bg-white'
            }`}
          />
          {errors.motivo && <p className="mt-1 text-xs text-red-600">{errors.motivo}</p>}
        </div>

        {errors._geral && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {errors._geral}
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" loading={saving}>
            Confirmar
          </Button>
        </div>
      </form>
    </Modal>
  )
}

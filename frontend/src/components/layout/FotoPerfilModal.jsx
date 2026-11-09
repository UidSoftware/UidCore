import { useState } from 'react'
import api from '../../api/client.js'
import { extractErrorMessage } from '../../utils/errors.js'
import useAuthStore from '../../stores/authStore.js'
import Modal from '../ui/Modal.jsx'
import Button from '../ui/Button.jsx'
import Avatar from '../ui/Avatar.jsx'

/**
 * Modal de foto de perfil do usuário logado (escolher com preview, salvar,
 * remover). Saiu do Header quando a foto foi para o topo da Sidebar; a
 * lógica e os endpoints são os mesmos da Manutenção #93
 * (POST/DELETE /accounts/me/foto/).
 */
export default function FotoPerfilModal({ onClose }) {
  const user = useAuthStore((s) => s.user)
  const [arquivoFoto, setArquivoFoto] = useState(null)
  const [previewFoto, setPreviewFoto] = useState(null)
  const [fotoErro, setFotoErro] = useState('')
  const [salvandoFoto, setSalvandoFoto] = useState(false)
  const [removendoFoto, setRemovendoFoto] = useState(false)

  const fechar = () => {
    if (previewFoto) URL.revokeObjectURL(previewFoto)
    onClose()
  }

  const handleArquivoFotoChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (previewFoto) URL.revokeObjectURL(previewFoto)
    setArquivoFoto(file)
    setPreviewFoto(URL.createObjectURL(file))
    setFotoErro('')
  }

  const enviarFoto = async () => {
    if (!arquivoFoto) return
    setFotoErro('')
    setSalvandoFoto(true)
    try {
      const form = new FormData()
      form.append('foto', arquivoFoto)
      const { data } = await api.post('/accounts/me/foto/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      useAuthStore.getState().setUser({ ...user, foto_url: data.foto_url })
      fechar()
    } catch (error) {
      setFotoErro(error?.response?.data?.erro || extractErrorMessage(error, 'Erro ao enviar foto.'))
    } finally {
      setSalvandoFoto(false)
    }
  }

  const removerFoto = async () => {
    if (!window.confirm('Remover sua foto de perfil?')) return
    setFotoErro('')
    setRemovendoFoto(true)
    try {
      const { data } = await api.delete('/accounts/me/foto/')
      useAuthStore.getState().setUser({ ...user, foto_url: data.foto_url })
      fechar()
    } catch (error) {
      setFotoErro(extractErrorMessage(error, 'Erro ao remover foto.'))
    } finally {
      setRemovendoFoto(false)
    }
  }

  return (
    <Modal title="Foto de perfil" onClose={fechar}>
      <div className="space-y-4">
        <div className="flex flex-col items-center gap-3">
          <Avatar
            foto={previewFoto || user?.foto_url}
            nome={user?.nome_completo || user?.email}
            size="lg"
            className="mx-auto"
          />
          {!previewFoto && user?.foto_url && (
            <button
              type="button"
              onClick={removerFoto}
              disabled={removendoFoto || salvandoFoto}
              className="text-sm text-red-600 hover:underline dark:text-red-400 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {removendoFoto ? 'Removendo...' : 'Remover foto'}
            </button>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="foto-perfil-input">
            <span className="sr-only">Escolher foto</span>
          </label>
          <input
            id="foto-perfil-input"
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleArquivoFotoChange}
            disabled={salvandoFoto || removendoFoto}
          />
          <Button
            type="button"
            variant="secondary"
            disabled={salvandoFoto || removendoFoto}
            onClick={() => document.getElementById('foto-perfil-input')?.click()}
          >
            Escolher foto
          </Button>
          {arquivoFoto && (
            <p className="text-xs text-gray-500 dark:text-slate-400">{arquivoFoto.name} selecionada</p>
          )}
        </div>

        {fotoErro && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 dark:bg-red-950/40 dark:border-red-800">
            <p className="text-sm text-red-700 dark:text-red-300">{fotoErro}</p>
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={fechar}>Cancelar</Button>
          <Button type="button" disabled={!arquivoFoto} loading={salvandoFoto} onClick={enviarFoto}>
            Salvar
          </Button>
        </div>
      </div>
    </Modal>
  )
}

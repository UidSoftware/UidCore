import { useEffect, useState } from 'react'
import { LifeBuoy } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth.js'
import { useTheme } from '../../hooks/useTheme.js'
import api from '../../api/client.js'
import { extractErrorMessage } from '../../utils/errors.js'
import { APP_NAME } from '../../utils/appConfig.js'
import Modal from '../ui/Modal.jsx'
import Input from '../ui/Input.jsx'
import Select from '../ui/Select.jsx'
import Button from '../ui/Button.jsx'

const EMPTY_SENHA_FORM = { senha_atual: '', senha_nova: '', confirmar: '' }
const EMPTY_PROBLEMA_FORM = { descricao: '', prioridade: 'MEDIA' }
const OPCOES_PRIORIDADE = [
  { value: 'BAIXA', label: 'Baixa' },
  { value: 'MEDIA', label: 'Média' },
  { value: 'ALTA', label: 'Alta (impede o trabalho)' },
]

export default function Header({ onMenuOpen }) {
  const { logout } = useAuth()
  const { isDark, toggleTheme } = useTheme()

  const [modalSenha, setModalSenha] = useState(false)
  const [senhaForm, setSenhaForm] = useState(EMPTY_SENHA_FORM)
  const [senhaErro, setSenhaErro] = useState('')
  const [senhaSucesso, setSenhaSucesso] = useState(false)
  const [salvandoSenha, setSalvandoSenha] = useState(false)

  const [relatoAtivo, setRelatoAtivo] = useState(false)
  const [modalProblema, setModalProblema] = useState(false)
  const [problemaForm, setProblemaForm] = useState(EMPTY_PROBLEMA_FORM)
  const [problemaErro, setProblemaErro] = useState('')
  const [problemaEnviado, setProblemaEnviado] = useState(false)
  const [enviandoProblema, setEnviandoProblema] = useState(false)

  useEffect(() => {
    api.get('/suporte/relatar-problema/')
      .then(({ data }) => setRelatoAtivo(data.ativo))
      .catch(() => setRelatoAtivo(false))
  }, [])

  const abrirModalProblema = () => {
    setProblemaForm(EMPTY_PROBLEMA_FORM)
    setProblemaErro('')
    setProblemaEnviado(false)
    setModalProblema(true)
  }

  const enviarProblema = async (e) => {
    e.preventDefault()
    setProblemaErro('')
    setEnviandoProblema(true)
    try {
      await api.post('/suporte/relatar-problema/', problemaForm)
      setProblemaEnviado(true)
    } catch (err) {
      setProblemaErro(extractErrorMessage(err))
    } finally {
      setEnviandoProblema(false)
    }
  }

  const abrirModalSenha = () => {
    setSenhaForm(EMPTY_SENHA_FORM)
    setSenhaErro('')
    setSenhaSucesso(false)
    setModalSenha(true)
  }

  const salvarSenha = async (e) => {
    e.preventDefault()
    setSenhaErro('')
    if (senhaForm.senha_nova.length < 6) { setSenhaErro('A nova senha deve ter pelo menos 6 caracteres.'); return }
    if (senhaForm.senha_nova !== senhaForm.confirmar) { setSenhaErro('As senhas não coincidem.'); return }
    setSalvandoSenha(true)
    try {
      await api.post('/accounts/alterar-senha/', {
        senha_atual: senhaForm.senha_atual, senha_nova: senhaForm.senha_nova,
      })
      setSenhaSucesso(true)
    } catch (error) {
      setSenhaErro(error?.response?.data?.erro || extractErrorMessage(error, 'Erro ao alterar senha.'))
    } finally {
      setSalvandoSenha(false)
    }
  }

  return (
    <header className="h-16 bg-white dark:bg-navy-900 border-b border-gray-200 dark:border-navy-600 flex items-center px-4 md:px-6 shrink-0">
      <div className="flex-1 flex items-center">
        <button
          onClick={onMenuOpen}
          className="md:hidden p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:text-slate-400 dark:hover:bg-navy-700 transition-colors"
          aria-label="Abrir menu"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>

      {/* Centro: nome do sistema (foto e nome do usuário ficam no topo da Sidebar) */}
      <div className="flex flex-col items-center leading-none text-center">
        <span className="text-base font-bold text-primary-600 dark:text-violet-400 tracking-tight">{APP_NAME}</span>
        <span className="text-[10px] uppercase tracking-widest text-gray-400 dark:text-slate-500 mt-1">Sistema</span>
      </div>

      <div className="flex-1 flex items-center justify-end gap-1 sm:gap-2">
        <button
          onClick={toggleTheme}
          aria-label={isDark ? 'Ativar modo claro' : 'Ativar modo escuro'}
          title={isDark ? 'Ativar modo claro' : 'Ativar modo escuro'}
          className="w-9 h-9 flex items-center justify-center rounded-lg text-lg
                     text-gray-500 hover:bg-gray-100
                     dark:text-slate-400 dark:hover:bg-navy-700
                     transition-colors"
        >
          {isDark ? '☀️' : '🌙'}
        </button>
        {relatoAtivo && (
          <button
            onClick={abrirModalProblema}
            title="Relatar problema"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-slate-400 dark:hover:bg-navy-700 dark:hover:text-slate-200 transition-colors"
          >
            <LifeBuoy className="w-4 h-4" />
            <span className="hidden sm:block">Problema</span>
          </button>
        )}
        <button
          onClick={abrirModalSenha}
          title="Alterar senha"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-slate-400 dark:hover:bg-navy-700 dark:hover:text-slate-200 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          <span className="hidden sm:block">Senha</span>
        </button>
        <button
          onClick={logout}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-slate-400 dark:hover:bg-navy-700 dark:hover:text-slate-200 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          <span className="hidden sm:block">Sair</span>
        </button>
      </div>

      {modalSenha && (
        <Modal title="Alterar senha" onClose={() => setModalSenha(false)}>
          {senhaSucesso ? (
            <div className="text-center space-y-4">
              <p className="text-sm text-gray-600 dark:text-slate-300">Sua senha foi alterada com sucesso.</p>
              <Button onClick={() => setModalSenha(false)} className="w-full">Fechar</Button>
            </div>
          ) : (
            <form onSubmit={salvarSenha} className="space-y-4">
              {senhaErro && (
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 dark:bg-red-950/40 dark:border-red-800">
                  <p className="text-sm text-red-700 dark:text-red-300">{senhaErro}</p>
                </div>
              )}
              <Input
                label="Senha atual" type="password" autoComplete="current-password"
                value={senhaForm.senha_atual}
                onChange={(e) => setSenhaForm((f) => ({ ...f, senha_atual: e.target.value }))}
              />
              <Input
                label="Nova senha" type="password" autoComplete="new-password"
                value={senhaForm.senha_nova}
                onChange={(e) => setSenhaForm((f) => ({ ...f, senha_nova: e.target.value }))}
              />
              <Input
                label="Confirmar nova senha" type="password" autoComplete="new-password"
                value={senhaForm.confirmar}
                onChange={(e) => setSenhaForm((f) => ({ ...f, confirmar: e.target.value }))}
              />
              <div className="flex justify-end gap-3 pt-2">
                <Button type="button" variant="secondary" onClick={() => setModalSenha(false)}>Cancelar</Button>
                <Button type="submit" loading={salvandoSenha}>Salvar</Button>
              </div>
            </form>
          )}
        </Modal>
      )}

      {modalProblema && (
        <Modal title="Relatar problema" onClose={() => setModalProblema(false)}>
          {problemaEnviado ? (
            <div className="text-center space-y-4">
              <p className="text-sm text-gray-600 dark:text-slate-300">Recebemos seu relato. A Uid Software vai analisar.</p>
              <Button onClick={() => setModalProblema(false)} className="w-full">Fechar</Button>
            </div>
          ) : (
            <form onSubmit={enviarProblema} className="space-y-4">
              <div className="flex flex-col gap-1">
                <label htmlFor="problema-descricao" className="text-sm font-medium text-gray-700 dark:text-slate-300">O que aconteceu?</label>
                <textarea
                  id="problema-descricao"
                  rows={5}
                  maxLength={2000}
                  required
                  value={problemaForm.descricao}
                  onChange={(e) => setProblemaForm({ ...problemaForm, descricao: e.target.value })}
                  placeholder="Em qual tela, o que você tentou fazer e o que apareceu."
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm bg-white text-gray-900 dark:bg-navy-800 dark:border-navy-600 dark:text-slate-100"
                />
              </div>
              <Select
                label="Prioridade"
                value={problemaForm.prioridade}
                onChange={(e) => setProblemaForm({ ...problemaForm, prioridade: e.target.value })}
                options={OPCOES_PRIORIDADE}
              />
              {problemaErro && <p className="text-sm text-red-600 dark:text-red-400">{problemaErro}</p>}
              <div className="flex justify-end gap-3 pt-2">
                <Button type="button" variant="secondary" onClick={() => setModalProblema(false)}>Cancelar</Button>
                <Button type="submit" loading={enviandoProblema}>Enviar</Button>
              </div>
            </form>
          )}
        </Modal>
      )}
    </header>
  )
}

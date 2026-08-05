import { useEffect, useRef, useState } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'
import Modal from '../../../components/ui/Modal.jsx'
import Button from '../../../components/ui/Button.jsx'

/**
 * Modal "Escanear com câmera" (RF-18/19/20).
 *
 * Usa @zxing/library (BrowserMultiFormatReader) — escolhida entre
 * @zxing/library / html5-qrcode / quagga2 (RNF-09) por ser a mais leve das
 * três, decodificar direto de um <video> via getUserMedia sem exigir canvas
 * manual, e ter suporte nativo aos formatos de código de barras 1D usados em
 * produto (EAN-13, EAN-8, Code128 etc.) além de QR — quagga2 é mais pesada e
 * o html5-qrcode é focado em QR Code, com barcode 1D como adição posterior.
 *
 * Props:
 *   onClose()            — fecha o modal sem detecção (botão × ou "Fechar")
 *   onDetectado(codigo)   — código de barras decodificado com sucesso
 *   onPermissaoNegada()   — getUserMedia rejeitado por permissão do usuário
 */
export default function ModalScannerCamera({ onClose, onDetectado, onPermissaoNegada }) {
  const videoRef = useRef(null)
  const readerRef = useRef(null)
  const [status, setStatus] = useState('iniciando') // iniciando | ativo | nao_suportado

  useEffect(() => {
    let ativo = true

    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus('nao_suportado')
      return undefined
    }

    import('@zxing/library').then(({ BrowserMultiFormatReader }) => {
      if (!ativo) return
      const reader = new BrowserMultiFormatReader()
      readerRef.current = reader

      reader
        .decodeFromVideoDevice(undefined, videoRef.current, (result) => {
          if (!ativo || !result) return
          ativo = false
          reader.reset()
          onDetectado(result.getText())
        })
        .then(() => {
          if (ativo) setStatus('ativo')
        })
        .catch((err) => {
          if (!ativo) return
          if (err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError') {
            onPermissaoNegada()
          } else {
            setStatus('nao_suportado')
          }
        })
    })

    return () => {
      ativo = false
      readerRef.current?.reset()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (status === 'nao_suportado') {
    return (
      <Modal title="Escanear código de barras" onClose={onClose} maxW="max-w-md">
        <div className="text-center py-8">
          <AlertCircle size={20} className="mx-auto text-red-600 mb-2" />
          <p className="text-sm text-gray-600">
            Câmera não suportada neste navegador.
            <br />
            Use o leitor físico ou digite o código manualmente.
          </p>
          <div className="mt-4">
            <Button variant="secondary" size="sm" onClick={onClose}>
              Fechar
            </Button>
          </div>
        </div>
      </Modal>
    )
  }

  return (
    <Modal title="Escanear código de barras" onClose={onClose} maxW="max-w-md">
      <div className="relative rounded-lg overflow-hidden bg-black aspect-video">
        <video ref={videoRef} className="w-full h-full object-cover" autoPlay playsInline muted />
        {status === 'ativo' && (
          <div className="absolute inset-x-8 top-1/2 -translate-y-1/2 h-0.5 bg-primary-500/80" />
        )}
      </div>
      {status === 'iniciando' ? (
        <div className="flex items-center justify-center gap-2 py-4">
          <Loader2 size={16} className="text-gray-500 animate-spin" />
          <span className="text-sm text-gray-500">Iniciando câmera...</span>
        </div>
      ) : (
        <p className="text-xs text-gray-500 text-center mt-3">
          Aponte a câmera para o código de barras do produto
        </p>
      )}
    </Modal>
  )
}

export default function Modal({ title, onClose, children, maxW = 'max-w-lg' }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4 bg-black/50">
      <div className={`w-full ${maxW} bg-white rounded-2xl shadow-xl p-6 max-h-[90vh] overflow-y-auto`}>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            &times;
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

export default function Modal({ title, onClose, children, maxW = 'max-w-lg' }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4 bg-black/50">
      <div className={`w-full ${maxW} bg-white rounded-2xl shadow-xl p-6 max-h-[90vh] overflow-y-auto dark:bg-navy-800 dark:shadow-none dark:border dark:border-navy-600`}>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-gray-900 dark:text-slate-100">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none dark:text-slate-500 dark:hover:text-slate-300"
          >
            &times;
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

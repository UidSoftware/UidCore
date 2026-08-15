export default function Pagination({ page, totalPages, onPageChange }) {
  if (totalPages <= 1) return null
  return (
    <div className="flex justify-center gap-2 py-4">
      {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
        <button
          key={p}
          onClick={() => onPageChange(p)}
          className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
            p === page
              ? 'bg-primary-600 text-white dark:bg-violet-600'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-navy-800 dark:text-slate-400 dark:hover:bg-navy-700'
          }`}
        >
          {p}
        </button>
      ))}
    </div>
  )
}

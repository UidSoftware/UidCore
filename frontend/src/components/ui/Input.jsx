export default function Input({
  label,
  error,
  id,
  className = '',
  type = 'text',
  ...props
}) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')

  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-gray-700 dark:text-slate-300">
          {label}
        </label>
      )}
      <input
        id={inputId}
        type={type}
        className={`
          w-full rounded-lg border px-3 py-2 text-sm text-gray-900 placeholder-gray-400
          focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
          disabled:bg-gray-50 disabled:cursor-not-allowed
          dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500
          dark:disabled:bg-navy-900 dark:disabled:text-slate-500
          transition-colors duration-150
          ${error ? 'border-red-500 bg-red-50 dark:border-red-500 dark:bg-red-950/40' : 'border-gray-300 bg-white dark:border-navy-500 dark:bg-navy-800'}
          ${className}
        `}
        {...props}
      />
      {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}
    </div>
  )
}

const variantClass: Record<string, string> = {
  row: 'h-10 w-full rounded-md',
  card: 'h-40 w-full rounded-lg',
  text: 'h-4 w-3/4 rounded',
}

export function Skeleton({
  variant,
  count = 1,
}: {
  variant: 'row' | 'card' | 'text'
  count?: number
}) {
  const base = variantClass[variant] ?? variantClass.row
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <div
          key={i}
          className={`${base} animate-pulse bg-journal-surface`}
          aria-hidden="true"
        />
      ))}
    </>
  )
}

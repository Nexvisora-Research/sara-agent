import { cn } from '@/lib/utils'

const assetPath = (path: string) => `${import.meta.env.BASE_URL}${path.replace(/^\/+/, '')}`

// Brand badge: packaged Sara mark on a white tile, identical in light/dark.
// Fills the tile; size via className (default size-14).
export function BrandMark({ className, ...props }: React.ComponentProps<'span'>) {
  return (
    <span
      className={cn(
        'inline-flex size-14 shrink-0 items-center justify-center overflow-hidden rounded-md bg-white shadow-sm ring-1 ring-[color-mix(in_srgb,var(--ui-base)_6%,transparent)]',
        className
      )}
      {...props}
    >
      <img alt="" className="size-full object-cover" src={assetPath('Sara.png')} />
    </span>
  )
}

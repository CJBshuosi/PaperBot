import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function safeHref(url?: string | null) {
  if (!url) return null
  const trimmed = url.trim()
  if (!trimmed) return null
  const hasScheme = /^[a-zA-Z][a-zA-Z\d+.-]*:/.test(trimmed)
  if (!hasScheme) return trimmed
  try {
    const parsed = new URL(trimmed)
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? trimmed : null
  } catch {
    return null
  }
}

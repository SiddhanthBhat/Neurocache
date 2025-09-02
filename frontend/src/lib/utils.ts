/**
 * Utility to concatenate class names. Filters out falsey values and
 * joins the rest with a space. Useful for conditionally applying
 * Tailwind classes.
 */
export function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(" ");
}
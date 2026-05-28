const AVATAR_COLORS = [
  ['#D1FAE5', '#065F46'],
  ['#DBEAFE', '#1E40AF'],
  ['#FEF3C7', '#92400E'],
  ['#FCE7F3', '#9D174D'],
  ['#EDE9FE', '#5B21B6'],
  ['#FFEDD5', '#9A3412'],
  ['#F0FDF4', '#14532D'],
  ['#E0F2FE', '#075985'],
]

export function avatarColor(name = '') {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

export function initials(name = '') {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0].toUpperCase())
    .join('')
}

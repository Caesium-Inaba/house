/* 事件图标：24 视窗线性小图标，currentColor */

import type { JSX } from 'react'

const S = {
  width: 15,
  height: 15,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  flex: 'none',
}

export const IconHeart = () => (
  <svg {...S}>
    <path d="M12 20.5C7 16.5 3.5 13 3.5 9.2 3.5 6.6 5.5 4.5 8 4.5c1.6 0 3.1.8 4 2.1.9-1.3 2.4-2.1 4-2.1 2.5 0 4.5 2.1 4.5 4.7 0 3.8-3.5 7.3-8.5 11.3z" />
  </svg>
)

export const IconCradle = () => (
  <svg {...S}>
    <circle cx="12" cy="8" r="3.6" />
    <path d="M5.5 20c1-4.4 4-6.5 6.5-6.5s5.5 2.1 6.5 6.5z" />
  </svg>
)

export const IconRings = () => (
  <svg {...S}>
    <circle cx="9" cy="13" r="5.5" />
    <circle cx="15" cy="13" r="5.5" />
    <path d="M12 4.5l1.2 2.4h-2.4z" fill="currentColor" stroke="none" />
  </svg>
)

export const IconCandle = () => (
  <svg {...S}>
    <path d="M9 21h6M10 21v-8h4v8" />
    <path d="M12 3.2c1.6 1.8 2.4 3 2.4 4.3a2.4 2.4 0 1 1-4.8 0c0-1.3.8-2.5 2.4-4.3z" />
  </svg>
)

export const IconCrown = () => (
  <svg {...S}>
    <path d="M4 18h16M4 18L3 8l4.6 3.4L12 5l4.4 6.4L21 8l-1 10" />
  </svg>
)

export const IconFallenCrown = () => (
  <svg {...S}>
    <g transform="rotate(24 12 12)">
      <path d="M6 17h12M6 17L5 9l3.4 2.5L12 6l3.6 5.5L19 9l-.9 8" />
    </g>
    <path d="M4 20.5l3-3M7.5 20.5l-3-3" />
  </svg>
)

export const IconSprout = () => (
  <svg {...S}>
    <path d="M12 21v-8" />
    <path d="M12 13C12 9 9.8 7 6.5 6.8 6.6 10 8.8 12.6 12 13z" />
    <path d="M12 13c0-3.4 2.2-5.2 5.5-5.4-.1 3-2.3 5.1-5.5 5.4z" />
  </svg>
)

export const IconScroll = () => (
  <svg {...S}>
    <path d="M7 4h11a2 2 0 0 1 2 2v2h-4M7 4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2V8" />
    <path d="M9 9h6M9 12.5h6M9 16h4" />
  </svg>
)

export const IconTree = () => (
  <svg {...S}>
    <circle cx="12" cy="5" r="2.2" />
    <circle cx="6.5" cy="18" r="2.2" />
    <circle cx="17.5" cy="18" r="2.2" />
    <path d="M12 7.2v4M6.5 15.8v-2c0-1.6 2.2-2.6 5.5-2.6s5.5 1 5.5 2.6v2" />
  </svg>
)

export const IconSave = () => (
  <svg {...S}>
    <path d="M5 4h11l3 3v13H5z" />
    <path d="M8 4v5h7V4M8 20v-7h8v7" />
  </svg>
)

export const IconAuto = () => (
  <svg {...S}>
    <path d="M7 5l11 7-11 7z" />
  </svg>
)

export const IconPause = () => (
  <svg {...S}>
    <path d="M8 5v14M16 5v14" />
  </svg>
)

export const IconHourglass = () => (
  <svg {...S}>
    <path d="M6 3h12M6 21h12M8 3v3.5L12 11l4-4.5V3M8 21v-3.5l4-4.5 4 4.5V21" />
  </svg>
)

export const EVENT_ICONS: Record<string, () => JSX.Element> = {
  pregnancy: IconHeart,
  birth: IconCradle,
  marriage: IconRings,
  death: IconCandle,
  succession: IconCrown,
  extinction: IconFallenCrown,
  adulthood: IconSprout,
  chronicle: IconScroll,
}

export const EVENT_COLORS: Record<string, string> = {
  pregnancy: 'var(--verdant)',
  birth: 'var(--verdant)',
  marriage: '#c98ba8',
  death: 'var(--wax)',
  succession: 'var(--gold)',
  extinction: 'var(--wax)',
  adulthood: 'var(--steel)',
  chronicle: 'var(--ink-faint)',
}

export const EVENT_LABELS: Record<string, string> = {
  pregnancy: '有孕',
  birth: '诞生',
  marriage: '联姻',
  death: '离世',
  succession: '继承',
  extinction: '绝嗣',
  adulthood: '成年',
  chronicle: '记事',
}

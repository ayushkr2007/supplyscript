import { useEffect, useState } from 'react'

const NAV_ITEMS = [
  { id: 'overview', label: 'Dashboard', icon: '◧' },
  { id: 'prescriptions', label: 'Prescriptions', icon: '▤' },
  { id: 'decisions', label: 'Decisions', icon: '◷' },
  { id: 'analytics', label: 'Analytics', icon: '◈' },
]

export default function Sidebar() {
  const [active, setActive] = useState('overview')

  useEffect(() => {
    const sections = NAV_ITEMS.map((n) => document.getElementById(n.id)).filter(Boolean)
    if (sections.length === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)
        if (visible[0]) setActive(visible[0].target.id)
      },
      { rootMargin: '-15% 0px -70% 0px', threshold: [0, 0.25, 0.5, 1] }
    )
    sections.forEach((s) => observer.observe(s))
    return () => observer.disconnect()
  }, [])

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__logo">SP</div>
        <div>
          <p className="sidebar__brand-name">SupplyPrescript</p>
          <p className="sidebar__brand-sub">Decision Board</p>
        </div>
      </div>

      <nav className="sidebar__nav" aria-label="Sections">
        {NAV_ITEMS.map((item) => (
          <a
            key={item.id}
            href={`#${item.id}`}
            className={`sidebar__link ${active === item.id ? 'sidebar__link--active' : ''}`}
          >
            <span className="sidebar__link-icon" aria-hidden="true">{item.icon}</span>
            {item.label}
          </a>
        ))}
      </nav>

      <div className="sidebar__status">
        <span className="sidebar__status-dot" />
        System online
      </div>
    </aside>
  )
}

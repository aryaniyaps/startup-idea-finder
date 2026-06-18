import { useState } from 'react'
import { Dashboard } from './components/Dashboard'
import { SignalsView } from './components/SignalsView'
import { ProblemsView } from './components/ProblemsView'
import { ProfileView } from './components/ProfileView'

type View = 'dashboard' | 'signals' | 'problems' | 'profile'

const TABS: { key: View; label: string }[] = [
  { key: 'dashboard', label: 'Ideas' },
  { key: 'signals', label: 'Signals' },
  { key: 'problems', label: 'Problems' },
  { key: 'profile', label: 'Profile' },
]

export default function App() {
  const [currentView, setCurrentView] = useState<View>('dashboard')

  if (currentView === 'profile') {
    return <ProfileView onNavigateBack={() => setCurrentView('dashboard')} />
  }

  return (
    <div className="max-w-[1400px] mx-auto px-6 py-4 flex flex-col h-dvh">
      {/* Tab bar */}
      <nav className="flex gap-1 mb-4 shrink-0 border-b border-warm-border pb-0" role="tablist">
        {TABS.filter(t => t.key !== 'profile').map(tab => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={currentView === tab.key}
            onClick={() => setCurrentView(tab.key)}
            className={[
              'px-4 py-2.5 text-sm font-medium transition-colors duration-150',
              'border-b-2 -mb-[1px]',
              currentView === tab.key
                ? 'text-amber-gold border-amber-gold'
                : 'text-faded-ink border-transparent hover:text-lamplight-ink hover:border-warm-border',
            ].join(' ')}
          >
            {tab.label}
          </button>
        ))}
        <div className="flex-1" />
        <button
          onClick={() => setCurrentView('profile')}
          className="px-4 py-2.5 text-sm font-medium text-faded-ink hover:text-lamplight-ink transition-colors duration-150 border-b-2 border-transparent -mb-[1px]"
          aria-label="Configure profile"
          title="Founder Profile"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="inline-block mr-1.5 -mt-0.5">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
          Profile
        </button>
      </nav>

      {/* Content */}
      <div className="flex-1 min-h-0">
        {currentView === 'dashboard' && <Dashboard onNavigateToProfile={() => setCurrentView('profile')} />}
        {currentView === 'signals' && <SignalsView />}
        {currentView === 'problems' && <ProblemsView />}
      </div>
    </div>
  )
}

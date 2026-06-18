import { type FormEvent, useState, useCallback } from 'react'
import { Toast, useToast } from './Toast'

type TagList = string[]

function TagInput({
  label,
  tags,
  onAdd,
  onRemove,
  placeholder,
}: {
  label: string
  tags: TagList
  onAdd: (value: string) => void
  onRemove: (value: string) => void
  placeholder?: string
}) {
  const [input, setInput] = useState('')

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key !== 'Enter') return
      e.preventDefault()
      const trimmed = input.trim()
      if (trimmed === '') return
      onAdd(trimmed)
      setInput('')
    },
    [input, onAdd],
  )

  return (
    <div>
      <label className="block text-sm font-medium text-lamplight-ink mb-2">{label}</label>
      <div className="flex flex-wrap gap-2 mb-2">
        {tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 bg-amber-muted/20 text-amber-gold rounded-full px-3 py-1 text-sm"
          >
            {tag}
            <button
              type="button"
              onClick={() => onRemove(tag)}
              className="text-amber-muted hover:text-amber-gold transition-colors duration-150"
              aria-label={`Remove ${tag}`}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </span>
        ))}
      </div>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder ?? `Type and press Enter to add…`}
        className="w-full bg-expedition-black border border-warm-border rounded-md px-3 py-2 text-lamplight-ink text-sm placeholder:text-quiet-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-gold/40"
      />
    </div>
  )
}

function RangeSlider({
  label,
  value,
  onChange,
  min = 0,
  max = 100,
}: {
  label: string
  value: number
  onChange: (value: number) => void
  min?: number
  max?: number
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between items-baseline">
        <label className="text-sm font-medium text-lamplight-ink">{label}</label>
        <span className="text-sm text-amber-gold tabular-nums">{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 rounded-full appearance-none bg-expedition-black border border-warm-border cursor-pointer accent-amber-gold [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-amber-gold"
      />
    </div>
  )
}

export function ProfileView({ onNavigateBack }: { onNavigateBack?: () => void }) {
  const [skills, setSkills] = useState<TagList>([])
  const [industries, setIndustries] = useState<TagList>([])
  const [yearsExperience, setYearsExperience] = useState(0)
  const [technicalDepth, setTechnicalDepth] = useState(50)
  const [capitalAvailable, setCapitalAvailable] = useState(50)
  const [problemsExperienced, setProblemsExperienced] = useState('')
  const [antiPreferences, setAntiPreferences] = useState('')
  const { toast, showToast, dismiss } = useToast()

  const addTag = useCallback((setter: React.Dispatch<React.SetStateAction<TagList>>) => {
    return (value: string) => {
      setter((prev) => {
        if (prev.includes(value)) return prev
        return [...prev, value]
      })
    }
  }, [])

  const removeTag = useCallback((setter: React.Dispatch<React.SetStateAction<TagList>>) => {
    return (value: string) => {
      setter((prev) => prev.filter((t) => t !== value))
    }
  }, [])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    showToast('Profile saved')
  }

  return (
    <div className="max-w-[1400px] mx-auto px-6 py-4">
      <button
        type="button"
        onClick={() => onNavigateBack?.()}
        className="inline-flex items-center gap-1.5 text-sm text-faded-ink hover:text-lamplight-ink transition-colors duration-150 mb-6 cursor-pointer"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="15 18 9 12 15 6" />
        </svg>
        Back to Dashboard
      </button>

      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-amber-gold">Founder Profile</h1>
        <p className="text-faded-ink text-sm mt-1">
          Your skills and background improve founder-market-fit scoring.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="space-y-6 max-w-2xl">
        {/* Skills */}
        <section className="bg-journal-surface border border-warm-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-lamplight-ink mb-4">Skills</h2>
          <TagInput
            label="Technical & domain skills"
            tags={skills}
            onAdd={addTag(setSkills)}
            onRemove={removeTag(setSkills)}
            placeholder="e.g. Rust, distributed systems, ML…"
          />
        </section>

        {/* Industries */}
        <section className="bg-journal-surface border border-warm-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-lamplight-ink mb-4">Industries</h2>
          <TagInput
            label="Industries you know well"
            tags={industries}
            onAdd={addTag(setIndustries)}
            onRemove={removeTag(setIndustries)}
            placeholder="e.g. fintech, climate, logistics…"
          />
        </section>

        {/* Experience */}
        <section className="bg-journal-surface border border-warm-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-lamplight-ink mb-4">Experience</h2>
          <div className="space-y-5">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="years-experience" className="text-sm font-medium text-lamplight-ink">
                Years of experience
              </label>
              <input
                id="years-experience"
                type="number"
                min={0}
                max={60}
                value={yearsExperience}
                onChange={(e) => setYearsExperience(Math.max(0, Number(e.target.value)))}
                className="w-32 bg-expedition-black border border-warm-border rounded-md px-3 py-2 text-lamplight-ink text-sm placeholder:text-quiet-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-gold/40"
              />
            </div>
            <RangeSlider
              label="Technical depth"
              value={technicalDepth}
              onChange={setTechnicalDepth}
            />
            <RangeSlider
              label="Capital available"
              value={capitalAvailable}
              onChange={setCapitalAvailable}
            />
          </div>
        </section>

        {/* Problems Experienced */}
        <section className="bg-journal-surface border border-warm-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-lamplight-ink mb-4">Problems Experienced</h2>
          <label className="block text-sm font-medium text-lamplight-ink mb-2">
            Problems you&rsquo;ve encountered first-hand
          </label>
          <textarea
            value={problemsExperienced}
            onChange={(e) => setProblemsExperienced(e.target.value)}
            rows={4}
            placeholder="One per line…"
            className="w-full bg-expedition-black border border-warm-border rounded-md px-3 py-2 text-lamplight-ink text-sm placeholder:text-quiet-ink resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-gold/40"
          />
        </section>

        {/* Anti-preferences */}
        <section className="bg-journal-surface border border-warm-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-lamplight-ink mb-4">Anti-preferences</h2>
          <label className="block text-sm font-medium text-lamplight-ink mb-2">
            Industries or domains you want to avoid
          </label>
          <textarea
            value={antiPreferences}
            onChange={(e) => setAntiPreferences(e.target.value)}
            rows={4}
            placeholder="One per line…"
            className="w-full bg-expedition-black border border-warm-border rounded-md px-3 py-2 text-lamplight-ink text-sm placeholder:text-quiet-ink resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-gold/40"
          />
        </section>

        <button
          type="submit"
          className="bg-amber-gold text-expedition-black font-semibold px-6 py-2 rounded-md hover:bg-amber-hover transition duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-gold/40"
        >
          Save
        </button>
      </form>

      <Toast message={toast.message} visible={toast.visible} onDismiss={dismiss} />
    </div>
  )
}

import React from 'react'

export default function Header() {
  return (
    <header style={{
      height: 52,
      background: 'var(--bg2)',
      borderBottom: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      padding: '0 20px',
      gap: 12,
      flexShrink: 0,
    }}>
      {/* Logo mark */}
      <div style={{
        width: 28, height: 28,
        borderRadius: 6,
        background: 'linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 14, fontWeight: 700, color: '#fff',
      }}>G</div>

      <span style={{ fontWeight: 600, fontSize: 15, color: 'var(--text)' }}>
        SAP O2C Graph Explorer
      </span>

      <div style={{ flex: 1 }} />

      <div style={{
        display: 'flex', gap: 6, alignItems: 'center',
        fontSize: 12, color: 'var(--text3)',
      }}>
        <span style={{
          width: 7, height: 7, borderRadius: '50%',
          background: 'var(--accent2)', display: 'inline-block',
        }} />
        Neo4j · Groq · FastAPI · React Flow
      </div>
    </header>
  )
}

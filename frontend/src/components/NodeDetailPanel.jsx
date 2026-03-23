import React, { useState } from 'react'

const NODE_COLORS = {
  SalesOrder:'#7F77DD', SalesOrderItem:'#AFA9EC', Delivery:'#1D9E75',
  DeliveryItem:'#5DCAA5', BillingDocument:'#D85A30', BillingItem:'#F0997B',
  Payment:'#EF9F27', JournalEntry:'#639922', BusinessPartner:'#378ADD',
  Address:'#85B7EB', Product:'#E24B4A', Plant:'#888780',
}

function PropRow({ k, v }) {
  if (v === null || v === undefined || v === '') return null
  const display = typeof v === 'boolean' ? (v ? 'true' : 'false') : String(v)
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '1fr 1.5fr',
      gap: 6, padding: '4px 0',
      borderBottom: '1px solid var(--border)',
    }}>
      <span style={{ fontSize: 11, color: 'var(--text3)', wordBreak: 'break-all' }}>{k}</span>
      <span style={{
        fontSize: 11, color: 'var(--text)',
        wordBreak: 'break-all', fontFamily: 'JetBrains Mono, monospace',
      }}>{display.length > 60 ? display.slice(0, 60) + '…' : display}</span>
    </div>
  )
}

export default function NodeDetailPanel({ detail, loading, onClose }) {
  const [expanded, setExpanded] = useState(null)
  const color = NODE_COLORS[detail?.label] || '#7F77DD'

  return (
    <div style={{
      position: 'absolute', right: 12, top: 12, bottom: 12,
      width: 300, background: 'var(--bg2)',
      border: '1px solid var(--border)', borderRadius: 10,
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden', zIndex: 10,
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 12px',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 8,
        background: 'var(--bg3)',
      }}>
        <div style={{
          width: 10, height: 10, borderRadius: '50%',
          background: color, flexShrink: 0,
        }} />
        <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text)', flex: 1 }}>
          {loading ? 'Loading…' : `${detail?.label} records`}
        </span>
        <button onClick={onClose} style={{
          background: 'transparent', color: 'var(--text3)',
          fontSize: 16, padding: '0 4px', lineHeight: 1,
        }}>×</button>
      </div>

      {/* Record list */}
      <div style={{ flex: 1, overflow: 'auto', padding: 8 }}>
        {loading && (
          <div style={{ padding: 16, color: 'var(--text2)', fontSize: 12, textAlign: 'center' }}>
            Loading records…
          </div>
        )}
        {!loading && detail?.samples?.map((rec, i) => (
          <div key={i} style={{
            background: expanded === i ? 'var(--bg)' : 'var(--bg3)',
            border: '1px solid var(--border)',
            borderRadius: 6, marginBottom: 6, overflow: 'hidden',
          }}>
            {/* Record header */}
            <button
              onClick={() => setExpanded(expanded === i ? null : i)}
              style={{
                width: '100%', textAlign: 'left',
                background: 'transparent', color: 'var(--text)',
                padding: '8px 10px', fontSize: 11,
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                borderBottom: expanded === i ? '1px solid var(--border)' : 'none',
              }}
            >
              <span className="mono" style={{ color: color }}>
                {rec.properties?.id || rec.id || `Record ${i + 1}`}
              </span>
              <span style={{ color: 'var(--text3)', fontSize: 14 }}>
                {expanded === i ? '▲' : '▼'}
              </span>
            </button>

            {/* Expanded properties */}
            {expanded === i && (
              <div style={{ padding: '6px 10px' }}>
                {Object.entries(rec.properties || {})
                  .filter(([k]) => !k.startsWith('_'))
                  .map(([k, v]) => <PropRow key={k} k={k} v={v} />)}
              </div>
            )}
          </div>
        ))}

        {!loading && detail?.samples?.length === 0 && (
          <div style={{ padding: 16, color: 'var(--text3)', fontSize: 12, textAlign: 'center' }}>
            No records found
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid var(--border)',
        fontSize: 11, color: 'var(--text3)',
      }}>
        Showing {detail?.samples?.length || 0} records · Click a row to expand
      </div>
    </div>
  )
}

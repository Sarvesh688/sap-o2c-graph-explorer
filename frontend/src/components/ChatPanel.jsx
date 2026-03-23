import React, { useState, useEffect, useRef } from 'react'
import { api } from '../api'

const CATEGORIES = ['All', 'Products', 'Trace', 'Exceptions', 'Customers', 'Payments', 'Orders', 'Plants']

function Message({ msg }) {
  const isUser = msg.role === 'user'
  const isError = msg.type === 'error' || msg.type === 'cypher_error'
  const [showCypher, setShowCypher] = useState(false)

  return (
    <div style={{
      display: 'flex',
      flexDirection: isUser ? 'row-reverse' : 'row',
      gap: 8, marginBottom: 14, alignItems: 'flex-start',
    }}>
      {/* Avatar */}
      <div style={{
        width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
        background: isUser ? 'var(--accent)' : 'var(--bg3)',
        border: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 11, fontWeight: 700, color: isUser ? '#fff' : 'var(--text2)',
      }}>
        {isUser ? 'U' : 'AI'}
      </div>

      <div style={{ maxWidth: '82%' }}>
        {/* Bubble */}
        <div style={{
          background: isUser ? 'var(--accent)' : isError ? '#2a1a1a' : 'var(--bg3)',
          border: `1px solid ${isUser ? 'transparent' : isError ? '#6b1f1f' : 'var(--border)'}`,
          borderRadius: isUser ? '12px 4px 12px 12px' : '4px 12px 12px 12px',
          padding: '10px 14px',
          fontSize: 13,
          color: isUser ? '#fff' : isError ? '#f87171' : 'var(--text)',
          lineHeight: 1.6,
          whiteSpace: 'pre-wrap',
        }}>
          {msg.loading ? (
            <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
              <LoadingDots />
            </span>
          ) : msg.message}
        </div>

        {/* Cypher toggle */}
        {!isUser && msg.cypher && (
          <div style={{ marginTop: 6 }}>
            <button
              onClick={() => setShowCypher(v => !v)}
              style={{
                background: 'transparent', color: 'var(--text3)',
                fontSize: 11, padding: '2px 6px',
                border: '1px solid var(--border)', borderRadius: 4,
              }}
            >
              {showCypher ? 'Hide' : 'Show'} Cypher ↗
            </button>

            {showCypher && (
              <pre style={{
                marginTop: 6, padding: '8px 10px',
                background: 'var(--bg)', border: '1px solid var(--border)',
                borderRadius: 6, fontSize: 11,
                color: '#a5f3fc', fontFamily: 'JetBrains Mono, monospace',
                overflow: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                maxHeight: 180,
              }}>
                {msg.cypher}
              </pre>
            )}
          </div>
        )}

        {/* Record count badge */}
        {!isUser && msg.record_count > 0 && (
          <div style={{
            marginTop: 4, fontSize: 11, color: 'var(--text3)',
          }}>
            {msg.record_count} record{msg.record_count !== 1 ? 's' : ''} found
          </div>
        )}
      </div>
    </div>
  )
}

function LoadingDots() {
  return (
    <span style={{ display: 'flex', gap: 4, padding: '2px 0' }}>
      {[0,1,2].map(i => (
        <span key={i} style={{
          width: 7, height: 7, borderRadius: '50%',
          background: 'var(--text3)',
          animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
          display: 'inline-block',
        }} />
      ))}
      <style>{`@keyframes pulse {0%,80%,100%{opacity:0.3;transform:scale(0.8)} 40%{opacity:1;transform:scale(1)}}`}</style>
    </span>
  )
}

export default function ChatPanel({ onHighlight, onNodeSelect }) {
  const [messages, setMessages]   = useState([{
    role: 'assistant',
    message: 'Ask me anything about the SAP Order-to-Cash dataset — sales orders, deliveries, billing documents, payments, customers, or products.',
    type: 'welcome',
  }])
  const [input, setInput]         = useState('')
  const [loading, setLoading]     = useState(false)
  const [examples, setExamples]   = useState([])
  const [filter, setFilter]       = useState('All')
  const [showExamples, setShowEx] = useState(true)
  const bottomRef                 = useRef(null)
  const inputRef                  = useRef(null)

  useEffect(() => {
    api.getExamples().then(setExamples).catch(() => {})
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const filteredExamples = filter === 'All'
    ? examples
    : examples.filter(e => e.category === filter)

  const send = async (text) => {
    const q = (text || input).trim()
    if (!q || loading) return
    setInput('')
    setShowEx(false)

    const userMsg = { role: 'user', message: q }
    const loadingMsg = { role: 'assistant', loading: true, message: '' }
    setMessages(prev => [...prev, userMsg, loadingMsg])
    setLoading(true)

    try {
      const resp = await api.sendQuery(q, [])
      setMessages(prev => [
        ...prev.slice(0, -1),
        {
          role: 'assistant',
          message: resp.message,
          cypher: resp.cypher,
          type: resp.type,
          record_count: resp.record_count || 0,
          highlighted_nodes: resp.highlighted_nodes || [],
        }
      ])
      if (resp.highlighted_nodes?.length) {
        onHighlight?.(resp.highlighted_nodes)
      }
    } catch (err) {
      setMessages(prev => [
        ...prev.slice(0, -1),
        {
          role: 'assistant',
          message: 'Error: ' + (err.response?.data?.detail || err.message),
          type: 'error',
        }
      ])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      background: 'var(--bg2)',
    }}>
      {/* Panel header */}
      <div style={{
        padding: '10px 16px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'var(--bg3)', flexShrink: 0,
      }}>
        <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text)' }}>
          Query Interface
        </span>
        <button
          onClick={() => { setMessages([{role:'assistant', message:'Chat cleared. Ask me a new question.', type:'info'}]); setShowEx(true); onHighlight?.([]); }}
          style={{
            background: 'transparent', color: 'var(--text3)',
            fontSize: 11, padding: '2px 8px',
            border: '1px solid var(--border)', borderRadius: 4,
          }}
        >
          Clear
        </button>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: 'auto', padding: '14px 12px' }}>
        {messages.map((msg, i) => <Message key={i} msg={msg} />)}

        {/* Example queries panel */}
        {showExamples && examples.length > 0 && (
          <div style={{ marginTop: 8 }}>
            {/* Category filter */}
            <div style={{
              display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: 10,
            }}>
              {CATEGORIES.map(cat => (
                <button
                  key={cat}
                  onClick={() => setFilter(cat)}
                  style={{
                    padding: '3px 9px', borderRadius: 12, fontSize: 11,
                    background: filter === cat ? 'var(--accent)' : 'var(--bg3)',
                    color: filter === cat ? '#fff' : 'var(--text2)',
                    border: `1px solid ${filter === cat ? 'var(--accent)' : 'var(--border)'}`,
                  }}
                >{cat}</button>
              ))}
            </div>

            {/* Example chips */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              {filteredExamples.map(ex => (
                <button
                  key={ex.id}
                  onClick={() => send(ex.question)}
                  style={{
                    background: 'var(--bg3)', border: '1px solid var(--border)',
                    borderRadius: 7, padding: '8px 12px',
                    textAlign: 'left', color: 'var(--text)',
                    fontSize: 12, lineHeight: 1.5,
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    gap: 8,
                  }}
                >
                  <span>{ex.question}</span>
                  <span style={{
                    fontSize: 10, color: 'var(--accent)',
                    background: 'rgba(127,119,221,0.12)',
                    borderRadius: 4, padding: '1px 6px', flexShrink: 0,
                  }}>{ex.category}</span>
                </button>
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={{
        padding: '10px 12px', borderTop: '1px solid var(--border)',
        background: 'var(--bg3)', flexShrink: 0,
      }}>
        <div style={{
          display: 'flex', gap: 8, alignItems: 'flex-end',
          background: 'var(--bg)', border: '1px solid var(--border)',
          borderRadius: 10, padding: '8px 10px',
        }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask about orders, deliveries, billing…"
            rows={2}
            disabled={loading}
            style={{
              flex: 1, background: 'transparent', border: 'none',
              color: 'var(--text)', fontSize: 13, lineHeight: 1.5,
              resize: 'none', maxHeight: 120,
            }}
          />
          <button
            onClick={() => send()}
            disabled={loading || !input.trim()}
            style={{
              background: loading || !input.trim() ? 'var(--bg3)' : 'var(--accent)',
              color: loading || !input.trim() ? 'var(--text3)' : '#fff',
              borderRadius: 8, padding: '7px 14px',
              fontSize: 13, fontWeight: 600, flexShrink: 0,
              border: '1px solid var(--border)',
            }}
          >
            {loading ? '…' : '↑'}
          </button>
        </div>
        <div style={{ fontSize: 10, color: 'var(--text3)', marginTop: 5, textAlign: 'center' }}>
          Enter to send · Shift+Enter for new line · Queries are restricted to this dataset
        </div>
      </div>
    </div>
  )
}

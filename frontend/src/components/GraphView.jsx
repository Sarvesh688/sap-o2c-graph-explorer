import React, { useEffect, useState, useCallback } from 'react'
import ReactFlow, {
  Background, Controls, MiniMap,
  useNodesState, useEdgesState,
  MarkerType
} from 'reactflow'
import 'reactflow/dist/style.css'
import { api } from '../api'
import NodeDetailPanel from './NodeDetailPanel'

const NODE_COLORS = {
  SalesOrder:       '#7F77DD',
  SalesOrderItem:   '#AFA9EC',
  Delivery:         '#1D9E75',
  DeliveryItem:     '#5DCAA5',
  BillingDocument:  '#D85A30',
  BillingItem:      '#F0997B',
  Payment:          '#EF9F27',
  JournalEntry:     '#639922',
  BusinessPartner:  '#378ADD',
  Address:          '#85B7EB',
  Product:          '#E24B4A',
  Plant:            '#888780',
}

function EntityNode({ data }) {
  const highlighted = data.highlighted
  const color = data.color || '#7F77DD'
  return (
    <div style={{
      background: highlighted ? color : 'var(--bg3)',
      border: `2px solid ${highlighted ? color : 'var(--border)'}`,
      borderRadius: 10,
      padding: '10px 16px',
      minWidth: 160,
      cursor: 'pointer',
      boxShadow: highlighted ? `0 0 16px ${color}55` : 'none',
      transition: 'all 0.2s',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4,
      }}>
        <div style={{
          width: 10, height: 10, borderRadius: '50%',
          background: color, flexShrink: 0,
        }} />
        <span style={{
          fontWeight: 600, fontSize: 12,
          color: highlighted ? '#fff' : 'var(--text)',
        }}>{data.label}</span>
      </div>
      {data.count !== undefined && (
        <div style={{
          fontSize: 11, color: highlighted ? 'rgba(255,255,255,0.8)' : 'var(--text2)',
          paddingLeft: 18,
        }}>
          {data.count.toLocaleString()} records
        </div>
      )}
      {data.subtitle && (
        <div style={{
          fontSize: 10, color: 'var(--text3)', paddingLeft: 18, marginTop: 2,
        }}>
          {data.subtitle}
        </div>
      )}
    </div>
  )
}

const nodeTypes = { entityNode: EntityNode }

export default function GraphView({ highlightedNodes = [], onNodeSelect }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading]   = useState(true)
  const [detail, setDetail]     = useState(null)
  const [detailLoading, setDL]  = useState(false)

  useEffect(() => {
    api.getGraph().then(data => {
      setNodes(data.nodes.map(n => ({
        ...n,
        type: 'entityNode',
        data: { ...n.data, highlighted: highlightedNodes.includes(n.data.label) }
      })))
      setEdges(data.edges.map(e => ({
        ...e,
        type: 'default',
        markerEnd: { type: MarkerType.ArrowClosed, color: '#444' },
        labelStyle: { fill: '#94a3b8', fontSize: 10 },
        labelBgStyle: { fill: 'var(--bg2)', fillOpacity: 0.9 },
        style: { stroke: '#444', strokeWidth: 1.5 },
      })))
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  // Update highlights when highlightedNodes changes
  useEffect(() => {
    setNodes(prev => prev.map(n => ({
      ...n,
      data: {
        ...n.data,
        highlighted: highlightedNodes.some(id =>
          id === n.data.label || id === n.data.id || id === n.id
        )
      }
    })))
  }, [highlightedNodes])

  const onNodeClick = useCallback(async (event, node) => {
    const label = node.data?.label
    if (!label) return
    setDL(true)
    try {
      const samples = await api.getEntitySample(label, 15)
      setDetail({ label, samples })
      onNodeSelect?.({ label, samples })
    } catch (e) {
      console.error(e)
    } finally {
      setDL(false)
    }
  }, [onNodeSelect])

  if (loading) return (
    <div style={{
      height: '100%', display: 'flex', alignItems: 'center',
      justifyContent: 'center', color: 'var(--text2)', fontSize: 14,
    }}>
      <span>Loading graph…</span>
    </div>
  )

  return (
    <div style={{ height: '100%', position: 'relative' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={2}
        style={{ background: 'var(--bg)' }}
      >
        <Background color="#2a3045" gap={24} size={1} />
        <Controls style={{
          background: 'var(--bg2)', border: '1px solid var(--border)',
          borderRadius: 8, overflow: 'hidden',
        }} />
        <MiniMap
          style={{ background: 'var(--bg2)', border: '1px solid var(--border)' }}
          nodeColor={n => n.data?.color || '#444'}
          maskColor="rgba(15,17,23,0.8)"
        />
      </ReactFlow>

      {/* Legend */}
      <div style={{
        position: 'absolute', top: 12, left: 12,
        background: 'var(--bg2)', border: '1px solid var(--border)',
        borderRadius: 8, padding: '10px 14px',
        fontSize: 11, color: 'var(--text2)',
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px',
        maxWidth: 280,
      }}>
        <div style={{ gridColumn:'1/-1', fontWeight:600, color:'var(--text)', marginBottom:4, fontSize:12 }}>
          Entity types
        </div>
        {Object.entries(NODE_COLORS).map(([label, color]) => (
          <div key={label} style={{ display:'flex', alignItems:'center', gap:5 }}>
            <div style={{ width:8, height:8, borderRadius:'50%', background:color, flexShrink:0 }} />
            <span style={{ fontSize:10 }}>{label}</span>
          </div>
        ))}
      </div>

      {/* Node detail panel */}
      {(detail || detailLoading) && (
        <NodeDetailPanel
          detail={detail}
          loading={detailLoading}
          onClose={() => setDetail(null)}
        />
      )}
    </div>
  )
}

import React, { useState } from 'react'
import GraphView from './components/GraphView'
import ChatPanel from './components/ChatPanel'
import Header from './components/Header'

export default function App() {
  const [highlightedNodes, setHighlightedNodes] = useState([])
  const [selectedNode, setSelectedNode]         = useState(null)

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100vh', background:'var(--bg)' }}>
      <Header />
      <div style={{ display:'flex', flex:1, overflow:'hidden' }}>
        {/* Left: Graph */}
        <div style={{ flex:1, minWidth:0, borderRight:'1px solid var(--border)', position:'relative' }}>
          <GraphView
            highlightedNodes={highlightedNodes}
            onNodeSelect={setSelectedNode}
            selectedNode={selectedNode}
          />
        </div>
        {/* Right: Chat */}
        <div style={{ width:420, flexShrink:0, display:'flex', flexDirection:'column' }}>
          <ChatPanel
            onHighlight={setHighlightedNodes}
            onNodeSelect={setSelectedNode}
          />
        </div>
      </div>
    </div>
  )
}

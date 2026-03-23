import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || ''

export const api = {
  getGraph:        ()           => axios.get(`${BASE}/api/graph`).then(r => r.data),
  getEntitySample: (label, n)   => axios.get(`${BASE}/api/graph/entity/${label}?limit=${n||20}`).then(r => r.data),
  getNodeDetail:   (label, id)  => axios.post(`${BASE}/api/graph/node`, {label, id}).then(r => r.data),
  getFlowGraph:    (soId)       => axios.get(`${BASE}/api/graph/flow/${soId}`).then(r => r.data),
  sendQuery:       (msg, hist)  => axios.post(`${BASE}/api/query`, {message: msg, history: hist||[]}).then(r => r.data),
  getExamples:     ()           => axios.get(`${BASE}/api/examples`).then(r => r.data),
}

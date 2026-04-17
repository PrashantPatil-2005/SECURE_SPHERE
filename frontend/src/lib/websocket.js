import { io } from 'socket.io-client';

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
let socket = null;

export function connectSocket(handlers) {
  if (socket) socket.disconnect();

  socket = io(BASE, {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: Infinity,
  });

  socket.on('connect', () => handlers.onConnect?.());
  socket.on('disconnect', () => handlers.onDisconnect?.());
  socket.on('new_event', (ev) => handlers.onEvent?.(ev));
  socket.on('new_incident', (inc) => handlers.onIncident?.(inc));
  socket.on('risk_update', (data) => handlers.onRiskUpdate?.(data));
  socket.on('summary_update', (data) => handlers.onSummary?.(data));
  socket.on('metrics_update', (data) => handlers.onMetrics?.(data));
  socket.on('timeline_update', (data) => handlers.onTimeline?.(data));
  socket.on('initial_state', (data) => handlers.onInitialState?.(data));
  socket.on('full_refresh', () => handlers.onFullRefresh?.());
  socket.on('incident_status_change', (data) => handlers.onIncidentStatusChange?.(data));

  return socket;
}

export function disconnectSocket() {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
}

export function getSocket() {
  return socket;
}

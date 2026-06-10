import { io } from 'socket.io-client';

const BASE = import.meta.env.VITE_API_URL ?? '';
let socket = null;

function currentToken() {
  try {
    return (
      localStorage.getItem('securisphere_token') ||
      sessionStorage.getItem('securisphere_token') ||
      ''
    );
  } catch {
    return '';
  }
}

export function connectSocket(handlers) {
  if (socket) socket.disconnect();

  const opts = {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: Infinity,
    // Function form so each (re)connection grabs the freshest token after an
    // access-token refresh. Backend rejects the handshake without a valid JWT.
    auth: (cb) => cb({ token: currentToken() }),
  };
  socket = BASE ? io(BASE, opts) : io(opts);

  socket.on('connect', () => handlers.onConnect?.());
  socket.on('disconnect', () => handlers.onDisconnect?.());
  socket.on('connect_error', (err) => handlers.onConnectError?.(err));
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

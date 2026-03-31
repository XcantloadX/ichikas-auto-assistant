/**
 * Typed WebSocket client with RPC (request-response) and event subscription.
 *
 * Protocol (same as Python server):
 *  Client → Server:  { type:"call",   id, method, params }
 *  Server → Client:  { type:"result", id, ok, data | error }
 *  Server → Client:  { type:"event",  name, data }
 */

import type { ProgressEvent } from '@/types';

export type EventCallback<T = unknown> = (data: T) => void;
export type UnsubscribeFn = () => void;

export interface RpcError extends Error {
  rpcError: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// WsClient
// ─────────────────────────────────────────────────────────────────────────────

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export type StatusChangeCallback = (status: ConnectionStatus) => void;

export class WsClient {
  private _ws: WebSocket | null = null;
  private _url: string;
  private _pendingCalls = new Map<string, {
    resolve: (data: unknown) => void;
    reject: (err: Error) => void;
  }>();
  private _eventListeners = new Map<string, Set<EventCallback>>();
  private _statusListeners = new Set<StatusChangeCallback>();
  private _status: ConnectionStatus = 'disconnected';
  private _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _destroyed = false;
  private _reconnectDelayMs = 2000;

  constructor(url: string) {
    this._url = url;
  }

  get status(): ConnectionStatus {
    return this._status;
  }

  // ── lifecycle ──────────────────────────────────────────────────────────────

  connect(): void {
    if (this._destroyed) return;
    if (this._ws && this._ws.readyState <= WebSocket.OPEN) return;
    this._setStatus('connecting');
    try {
      const ws = new WebSocket(this._url);
      this._ws = ws;

      ws.onopen = () => {
        this._reconnectDelayMs = 2000;
        this._setStatus('connected');
      };

      ws.onclose = () => {
        this._ws = null;
        this._rejectAllPending('WebSocket closed');
        if (!this._destroyed) {
          this._setStatus('disconnected');
          this._scheduleReconnect();
        }
      };

      ws.onerror = () => {
        this._setStatus('error');
      };

      ws.onmessage = (evt) => {
        this._handleMessage(evt.data);
      };
    } catch {
      this._setStatus('error');
      this._scheduleReconnect();
    }
  }

  disconnect(): void {
    this._destroyed = true;
    if (this._reconnectTimer !== null) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    this._ws?.close();
    this._ws = null;
    this._rejectAllPending('Client disconnected');
    this._setStatus('disconnected');
  }

  // ── RPC ───────────────────────────────────────────────────────────────────

  call<T = unknown>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      if (!this._ws || this._ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket not connected'));
        return;
      }
      const id = crypto.randomUUID();
      this._pendingCalls.set(id, {
        resolve: resolve as (data: unknown) => void,
        reject,
      });
      this._ws.send(JSON.stringify({ type: 'call', id, method, params }));
    });
  }

  // ── events ────────────────────────────────────────────────────────────────

  on<T = unknown>(eventName: string, cb: EventCallback<T>): UnsubscribeFn {
    if (!this._eventListeners.has(eventName)) {
      this._eventListeners.set(eventName, new Set());
    }
    this._eventListeners.get(eventName)!.add(cb as EventCallback);
    return () => this._eventListeners.get(eventName)?.delete(cb as EventCallback);
  }

  onStatusChange(cb: StatusChangeCallback): UnsubscribeFn {
    this._statusListeners.add(cb);
    return () => this._statusListeners.delete(cb);
  }

  // ── private ───────────────────────────────────────────────────────────────

  private _handleMessage(raw: string): void {
    let msg: Record<string, unknown>;
    try {
      msg = JSON.parse(raw) as Record<string, unknown>;
    } catch {
      return;
    }

    if (msg.type === 'result') {
      const id = msg.id as string;
      const pending = this._pendingCalls.get(id);
      if (!pending) return;
      this._pendingCalls.delete(id);
      if (msg.ok) {
        pending.resolve(msg.data);
      } else {
        const err = new Error(msg.error as string) as RpcError;
        err.rpcError = msg.error as string;
        pending.reject(err);
      }
    } else if (msg.type === 'event') {
      const name = msg.name as string;
      const listeners = this._eventListeners.get(name);
      if (listeners) {
        listeners.forEach(cb => cb(msg.data));
      }
    }
  }

  private _rejectAllPending(reason: string): void {
    for (const { reject } of this._pendingCalls.values()) {
      reject(new Error(reason));
    }
    this._pendingCalls.clear();
  }

  private _setStatus(s: ConnectionStatus): void {
    if (this._status === s) return;
    this._status = s;
    this._statusListeners.forEach(cb => cb(s));
  }

  private _scheduleReconnect(): void {
    if (this._destroyed) return;
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this._reconnectDelayMs = Math.min(this._reconnectDelayMs * 1.5, 15000);
      this.connect();
    }, this._reconnectDelayMs);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Singleton client
// ─────────────────────────────────────────────────────────────────────────────

const _wsUrl = (() => {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${location.host}/ws`;
})();

export const wsClient = new WsClient(_wsUrl);

// Helper: subscribe to typed progress events
export function onProgressEvent(cb: EventCallback<ProgressEvent>): UnsubscribeFn {
  return wsClient.on<ProgressEvent>('progress', cb);
}

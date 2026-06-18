import { useEffect, useRef, useState } from 'react'

export interface WebSocketState {
  connected: boolean
  reconnecting: boolean
  lastMessage: unknown
}

export function useWebSocket(): WebSocketState {
  const [reconnecting, setReconnecting] = useState(false)
  const [connected, setConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<unknown>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const attemptRef = useRef(0)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true

    function connect() {
      if (!mountedRef.current) return

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws`

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        if (!mountedRef.current) return
        setConnected(true)
        setReconnecting(false)
        attemptRef.current = 0
      }

      ws.onmessage = (event) => {
        if (!mountedRef.current) return
        try {
          const parsed = JSON.parse(event.data)
          setLastMessage(parsed)
        } catch {
          setLastMessage(event.data)
        }
      }
      ws.onclose = () => {
        if (!mountedRef.current) return
        setConnected(false)
        setReconnecting(true)
        scheduleReconnect()
      }

      ws.onerror = () => {
        // onclose fires after onerror, so reconnect is handled in onclose
        ws.close()
      }
    }

    function scheduleReconnect() {
      if (!mountedRef.current) return
      const delay = Math.min(1000 * Math.pow(2, attemptRef.current), 30000)
      attemptRef.current += 1
      reconnectTimerRef.current = setTimeout(connect, delay)
    }

    connect()

    return () => {
      mountedRef.current = false
      if (reconnectTimerRef.current !== null) {
        clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.onclose = null // prevent reconnect on intentional close
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [])

  return { connected, reconnecting, lastMessage }
}

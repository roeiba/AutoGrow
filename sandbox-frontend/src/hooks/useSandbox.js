import { useState, useEffect, useRef } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function useSandbox() {
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)
  const [isCreating, setIsCreating] = useState(false)
  const wsRef = useRef(null)
  const sandboxIdRef = useRef(null)

  useEffect(() => {
    // Cleanup WebSocket on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const connectWebSocket = (sandboxId) => {
    const wsUrl = `ws://${window.location.hostname}:8000/api/v1/sandboxes/${sandboxId}/ws`
    
    try {
      const ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        console.log('WebSocket connected')
        // Send ping to keep connection alive
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, 30000)
        
        ws.pingInterval = pingInterval
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'pong') {
            return // Ignore pong messages
          }
          
          setProgress(data)
          
          // Close connection when completed or failed
          if (data.status === 'completed' || data.status === 'failed') {
            setIsCreating(false)
            if (data.status === 'failed') {
              setError(data.message || 'Sandbox creation failed')
            }
            setTimeout(() => {
              ws.close()
            }, 1000)
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setError('Connection error. Please try again.')
        setIsCreating(false)
      }
      
      ws.onclose = () => {
        console.log('WebSocket closed')
        if (ws.pingInterval) {
          clearInterval(ws.pingInterval)
        }
      }
      
      wsRef.current = ws
    } catch (err) {
      console.error('Failed to create WebSocket:', err)
      setError('Failed to establish connection')
      setIsCreating(false)
    }
  }

  const createSandbox = async (projectIdea) => {
    setIsCreating(true)
    setError(null)
    setProgress(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/sandboxes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_idea: projectIdea,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to create sandbox')
      }

      const data = await response.json()
      sandboxIdRef.current = data.sandbox_id

      // Connect to WebSocket for real-time updates
      connectWebSocket(data.sandbox_id)

    } catch (err) {
      console.error('Failed to create sandbox:', err)
      setError(err.message || 'Failed to create sandbox. Please try again.')
      setIsCreating(false)
    }
  }

  return {
    createSandbox,
    progress,
    error,
    isCreating,
  }
}

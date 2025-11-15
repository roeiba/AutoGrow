import { useState, useEffect, useRef } from 'react'
import Logger from '../utils/logger'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const logger = new Logger('SeedPlanter')

export function useSeedPlanter() {
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)
  const [isPlanting, setIsPlanting] = useState(false)
  const wsRef = useRef(null)
  const projectIdRef = useRef(null)

  useEffect(() => {
    // Cleanup WebSocket on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const connectWebSocket = (projectId) => {
    // Convert HTTP(S) URL to WS(S) URL
    const apiUrl = new URL(API_BASE_URL)
    const wsProtocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${apiUrl.host}/api/v1/projects/${projectId}/ws`
    
    logger.websocket(`Connecting to WebSocket: ${wsUrl}`)
    
    try {
      const ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        logger.success('WebSocket connected successfully')
        // Send ping to keep connection alive
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
            logger.debug('Sent ping to keep connection alive')
          }
        }, 30000)
        
        ws.pingInterval = pingInterval
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'pong') {
            logger.debug('Received pong from server')
            return // Ignore pong messages
          }
          
          logger.progress(data.message || 'Progress update', data.progress_percent || 0, data)
          setProgress(data)
          
          // Close connection when completed or failed
          if (data.status === 'completed' || data.status === 'failed') {
            setIsPlanting(false)
            if (data.status === 'failed') {
              logger.error('Project planting failed:', data.message)
              setError(data.message || 'Project planting failed')
            } else {
              logger.success('Project planted successfully!', data)
            }
            setTimeout(() => {
              ws.close()
            }, 1000)
          }
        } catch (err) {
          logger.error('Failed to parse WebSocket message:', err)
        }
      }
      
      ws.onerror = (error) => {
        logger.error('WebSocket error:', error)
        setError('Connection error. Please try again.')
        setIsPlanting(false)
      }
      
      ws.onclose = () => {
        logger.websocket('WebSocket connection closed')
        if (ws.pingInterval) {
          clearInterval(ws.pingInterval)
        }
      }
      
      wsRef.current = ws
    } catch (err) {
      logger.error('Failed to create WebSocket:', err)
      setError('Failed to establish connection')
      setIsPlanting(false)
    }
  }

  const plantProject = async (projectDescription) => {
    // Generate a project name from description
    const projectName = projectDescription
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, '')
      .trim()
      .split(/\s+/)
      .slice(0, 3)
      .join('-') || 'my-project'
    
    return plantSeed(projectName, projectDescription)
  }

  const plantSeed = async (projectName, projectDescription) => {
    logger.info(`🌱 Starting to plant project: ${projectName}`)
    logger.debug(`Description: ${projectDescription}`)
    
    setIsPlanting(true)
    setError(null)
    setProgress(null)

    try {
      logger.api(`POST ${API_BASE_URL}/api/v1/projects`)
      
      const response = await fetch(`${API_BASE_URL}/api/v1/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_name: projectName,
          project_description: projectDescription,
          mode: 'saas',
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        logger.error('API request failed:', errorData)
        throw new Error(errorData.detail || 'Failed to plant seed')
      }

      const data = await response.json()
      projectIdRef.current = data.project_id
      logger.success(`Project created with ID: ${data.project_id}`)
      logger.debug('Response data:', data)

      // Connect to WebSocket for real-time updates
      connectWebSocket(data.project_id)

    } catch (err) {
      logger.error('Failed to plant seed:', err)
      setError(err.message || 'Failed to plant seed. Please try again.')
      setIsPlanting(false)
    }
  }

  return {
    plantProject,
    plantSeed,
    progress,
    error,
    isPlanting,
  }
}

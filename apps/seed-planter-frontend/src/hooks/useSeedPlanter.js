import { useState, useEffect, useRef } from 'react'
import Logger from '../utils/logger'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const logger = new Logger('SeedPlanter')

export function useSeedPlanter() {
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)
  const [isPlanting, setIsPlanting] = useState(false)
  const taskIdRef = useRef(null)
  const pollingIntervalRef = useRef(null)

  useEffect(() => {
    // Cleanup polling on unmount
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
      }
    }
  }, [])

  const pollTaskStatus = async (taskId) => {
    try {
      logger.api(`GET ${API_BASE_URL}/api/v1/tasks/${taskId}`)
      
      const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}`)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        logger.error('Failed to fetch task status:', errorData)
        throw new Error(errorData.detail || 'Failed to fetch task status')
      }
      
      const data = await response.json()
      logger.progress(data.message || 'Progress update', data.progress_percent || 0, data)
      setProgress(data)
      
      // Stop polling when completed or failed
      if (data.status === 'completed' || data.status === 'failed') {
        setIsPlanting(false)
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current)
          pollingIntervalRef.current = null
        }
        
        if (data.status === 'failed') {
          logger.error('Project planting failed:', data.error_message || data.message)
          setError(data.error_message || data.message || 'Project planting failed')
        } else {
          logger.success('Project planted successfully!', data)
        }
      }
    } catch (err) {
      logger.error('Failed to poll task status:', err)
      setError(err.message || 'Failed to check task status')
      setIsPlanting(false)
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
    }
  }
  
  const startPolling = (taskId) => {
    logger.info(`Starting to poll task status: ${taskId}`)
    taskIdRef.current = taskId
    
    // Poll immediately
    pollTaskStatus(taskId)
    
    // Then poll every 2 seconds
    pollingIntervalRef.current = setInterval(() => {
      pollTaskStatus(taskId)
    }, 2000)
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
      taskIdRef.current = data.task_id
      logger.success(`Task created with ID: ${data.task_id}`)
      logger.debug('Response data:', data)

      // Start polling for task status
      startPolling(data.task_id)

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

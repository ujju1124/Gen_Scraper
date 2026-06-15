/**
 * SSE (Server-Sent Events) Service
 * Manages EventSource connections for real-time job status updates
 */

/**
 * Create an SSE connection to job status stream
 * @param {string} jobId - Job ID to monitor
 * @param {Function} onMessage - Callback for status updates
 * @param {Function} onError - Callback for connection errors
 * @returns {EventSource} EventSource instance
 */
export const createJobStatusStream = (jobId, onMessage, onError) => {
  // Use relative URL to go through Vite proxy
  const url = `/api/v1/jobs/${jobId}/stream`
  console.log('Creating SSE connection to:', url)
  
  const eventSource = new EventSource(url, { withCredentials: true })

  eventSource.addEventListener('status', (event) => {
    try {
      console.log('SSE status event received:', event.data)
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch (error) {
      console.error('Failed to parse SSE message:', error)
    }
  })

  eventSource.addEventListener('open', () => {
    console.log('SSE connection opened successfully')
  })

  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error)
    console.log('EventSource readyState:', eventSource.readyState)
    onError(error)
    eventSource.close()
  }

  return eventSource
}

/**
 * Close an SSE connection
 * @param {EventSource} eventSource - EventSource instance to close
 */
export const closeStream = (eventSource) => {
  if (eventSource) {
    eventSource.close()
  }
}
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8080'

async function parseResponse(response) {
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const backendMessage = payload.detail || payload.message || `Backend returned ${response.status}`
    throw new Error(backendMessage)
  }
  return payload
}

async function request(url, options) {
  try {
    return await parseResponse(await fetch(url, options))
  } catch (error) {
    console.error('MediMind API error:', error)
    if (error instanceof TypeError) {
      throw new Error(
        'Unable to connect to MediMind AI. Please make sure the backend server is running.',
        { cause: error },
      )
    }
    throw error
  }
}

export async function healthCheck() {
  return request(`${API_BASE_URL}/health`)
}

export async function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request(`${API_BASE_URL}/reports/upload`, {
    method: 'POST',
    body: formData,
  })
}

export async function chat(question, documentId, language = 'English', mode = 'patient') {
  return request(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, document_id: documentId || null, language, mode }),
  })
}

export async function listReports() {
  return request(`${API_BASE_URL}/reports`)
}

export async function getPatientHistory(patientId) {
  return request(`${API_BASE_URL}/patients/${encodeURIComponent(patientId)}/history`)
}

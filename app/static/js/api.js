/**
 * HandWrite Me — API Client Module
 * Maps all backend REST endpoints with error handling & environment auto-detection.
 */
class ApiClient {
  constructor() {
    this.baseUrl = this.determineBaseUrl();
  }

  determineBaseUrl() {
    if (window.HANDWRITE_API_URL) {
      const url = window.HANDWRITE_API_URL.replace(/\/+$/, '');
      return url.endsWith('/api/v1') ? url : `${url}/api/v1`;
    }
    const host = window.location.hostname || '127.0.0.1';
    const port = window.location.port;
    const protocol = window.location.protocol || 'http:';
    
    // If frontend is hosted directly by FastAPI on port 8000
    if (port === '8000') {
      return `${protocol}//${window.location.host}/api/v1`;
    }
    // Standalone frontend dev servers (Live Server on 5500, Vite 5173, etc.)
    if (port === '5500' || port === '3000' || port === '5173' || port === '8080') {
      return `${protocol}//${host}:8000/api/v1`;
    }
    // Production deployment on standard ports (80 / 443) served directly by backend
    if (port === '' || !port) {
      return `${protocol}//${window.location.host}/api/v1`;
    }
    // Fallback for standalone server on any other port
    return `${protocol}//${host}:8000/api/v1`;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = options.headers || {};

    if (!(options.body instanceof FormData) && !headers['Content-Type'] && options.body) {
      headers['Content-Type'] = 'application/json';
    }

    const config = {
      method: options.method || 'GET',
      headers: headers,
      body: options.body,
    };

    try {
      const response = await fetch(url, config);
      
      // Handle HTTP 204 No Content
      if (response.status === 204) {
        return { success: true };
      }

      const contentType = response.headers.get('content-type') || '';
      let data = null;
      if (contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        let errorMsg = 'An API error occurred';
        if (data && typeof data === 'object') {
          if (data.detail) {
            errorMsg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
          } else if (data.message) {
            errorMsg = data.message;
          }
        }
        throw new Error(errorMsg);
      }

      return data;
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('Unable to connect to the backend server. Please verify the server is running.');
      }
      throw error;
    }
  }

  // --- Profile Endpoints ---
  async listProfiles(skip = 0, limit = 100) {
    return this.request(`/handwriting-profiles/?skip=${skip}&limit=${limit}`);
  }

  async getProfile(id) {
    return this.request(`/handwriting-profiles/${id}`);
  }

  async createProfile(data) {
    return this.request('/handwriting-profiles/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateProfile(id, data) {
    return this.request(`/handwriting-profiles/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteProfile(id) {
    return this.request(`/handwriting-profiles/${id}`, {
      method: 'DELETE',
    });
  }

  // --- Character Sample Endpoints ---
  async listSamples(profileId) {
    return this.request(`/handwriting-profiles/${profileId}/samples`);
  }

  async getSample(profileId, sampleId) {
    return this.request(`/handwriting-profiles/${profileId}/samples/${sampleId}`);
  }

  async uploadSample(profileId, formData) {
    return this.request(`/handwriting-profiles/${profileId}/samples`, {
      method: 'POST',
      body: formData,
    });
  }

  async deleteSample(profileId, sampleId) {
    return this.request(`/handwriting-profiles/${profileId}/samples/${sampleId}`, {
      method: 'DELETE',
    });
  }

  // --- PDF Document Endpoints ---
  async listDocuments(params = {}) {
    const query = new URLSearchParams();
    if (params.skip !== undefined) query.append('skip', params.skip);
    if (params.limit !== undefined) query.append('limit', params.limit);
    if (params.profile_id) query.append('profile_id', params.profile_id);
    if (params.status) query.append('status', params.status);
    
    const queryString = query.toString() ? `?${query.toString()}` : '';
    return this.request(`/documents/${queryString}`);
  }

  async getDocument(id) {
    return this.request(`/documents/${id}`);
  }

  async getDocumentText(id) {
    return this.request(`/documents/${id}/text`);
  }

  async uploadDocument(formData) {
    return this.request('/documents/', {
      method: 'POST',
      body: formData,
    });
  }

  async deleteDocument(id) {
    return this.request(`/documents/${id}`, {
      method: 'DELETE',
    });
  }
}

// Global API instance
window.api = new ApiClient();

import axios from 'axios';

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1') + '/';

export const api = axios.create({
    baseURL: API_URL,
});

// ── Auth token helpers ────────────────────────────────────────────────────────
export function getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('access_token');
}

export function setToken(token: string) {
    localStorage.setItem('access_token', token);
}

export function clearToken() {
    localStorage.removeItem('access_token');
}

// ── Axios interceptor: attach Bearer token to every request ───────────────────
api.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    // Prevent browser caching for GET requests during polling
    if (config.method?.toLowerCase() === 'get') {
        config.headers['Cache-Control'] = 'no-cache';
        config.headers['Pragma'] = 'no-cache';
        config.headers['Expires'] = '0';
    }
    return config;
});

// ── Axios interceptor: redirect to login on 401 ───────────────────────────────
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            clearToken();
            if (typeof window !== 'undefined') {
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export async function login(email: string, password: string): Promise<string> {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await api.post<{ access_token: string; token_type: string }>(
        'login/access-token',
        formData.toString(),
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );
    const token = response.data.access_token;
    setToken(token);
    return token;
}

// ── Document types & API ──────────────────────────────────────────────────────
export interface Document {
    id: string;
    filename: string;
    original_path: string;
    mime_type: string;
    status: string;
    confidence_score?: number;
    extracted_data?: any;
    created_at: string;
}

export async function getAllDocuments(skip = 0, limit = 100) {
    const response = await api.get<Document[]>(`documents/`, {
        params: { skip, limit }
    });
    return response.data;
}

export async function getDocumentById(id: string) {
    const response = await api.get<Document>(`documents/${id}`);
    return response.data;
}

export async function updateDocumentStatus(id: string, status: string, extractedData?: any) {
    const response = await api.put<Document>(`documents/${id}`, {
        status,
        extracted_data: extractedData
    });
    return response.data;
}

export async function uploadDocument(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<Document>('documents/upload', formData);
    return response.data;
}

export const documentService = {
    getAll: getAllDocuments,
    getById: getDocumentById,
    updateStatus: updateDocumentStatus,
    upload: uploadDocument
};

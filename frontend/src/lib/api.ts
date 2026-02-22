import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

export const api = axios.create({
    baseURL: API_URL,
});

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
    const response = await api.get<Document[]>(`/documents/`, {
        params: { skip, limit }
    });
    return response.data;
}

export async function getDocumentById(id: string) {
    const response = await api.get<Document>(`/documents/${id}`);
    return response.data;
}

export async function updateDocumentStatus(id: string, status: string, extractedData?: any) {
    const response = await api.put<Document>(`/documents/${id}`, {
        status,
        extracted_data: extractedData
    });
    return response.data;
}

export async function uploadDocument(file: File) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<Document>('/documents/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
}

// Keep the old object for backward compatibility but using the new functions
export const documentService = {
    getAll: getAllDocuments,
    getById: getDocumentById,
    updateStatus: updateDocumentStatus,
    upload: uploadDocument
};

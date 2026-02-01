const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface FetchOptions extends RequestInit {
    token?: string;
}

class ApiError extends Error {
    constructor(public status: number, message: string) {
        super(message);
        this.name = 'ApiError';
    }
}

async function fetchApi<T>(
    endpoint: string,
    options: FetchOptions = {}
): Promise<T> {
    const { token, ...fetchOptions } = options;

    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...((options.headers as Record<string, string>) || {}),
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
        ...fetchOptions,
        headers,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new ApiError(response.status, error.detail || 'Request failed');
    }

    // Handle empty responses
    const text = await response.text();
    if (!text) return {} as T;

    return JSON.parse(text);
}

// Auth API
export const authApi = {
    login: (email: string, password: string) =>
        fetchApi<{ access_token: string; token_type: string }>('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        }),

    register: (orgName: string, email: string, password: string) =>
        fetchApi<{ access_token: string; token_type: string }>('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ org_name: orgName, email, password }),
        }),

    me: (token: string) =>
        fetchApi<User>('/auth/me', { token }),
};

// Clients API
export const clientsApi = {
    list: (token: string) =>
        fetchApi<Client[]>('/clients', { token }),

    get: (token: string, clientId: string) =>
        fetchApi<Client>(`/clients/${clientId}`, { token }),

    create: (token: string, data: { name: string; gstin?: string; pan?: string; fy?: string }) =>
        fetchApi<Client>('/clients', {
            method: 'POST',
            body: JSON.stringify(data),
            token,
        }),
};

// Documents API
export const documentsApi = {
    list: (token: string, clientId: string) =>
        fetchApi<Document[]>(`/clients/${clientId}/documents`, { token }),

    get: (token: string, documentId: string) =>
        fetchApi<Document>(`/documents/${documentId}`, { token }),

    upload: async (token: string, clientId: string, file: File, docType: string) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('doc_type', docType);

        const response = await fetch(
            `${API_URL}/clients/${clientId}/documents`,
            {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                },
                body: formData,
            }
        );

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
            throw new ApiError(response.status, error.detail);
        }

        return response.json();
    },

    runIngestion: (token: string, documentId: string) =>
        fetchApi<{ message: string; task_id: string }>(
            `/documents/${documentId}/run-ingestion`,
            { method: 'POST', token }
        ),

    getStatus: (token: string, documentId: string) =>
        fetchApi<{ status: string; document_id: string }>(
            `/documents/${documentId}/status`,
            { token }
        ),
};

// Runs API
export const runsApi = {
    list: (token: string, clientId: string) =>
        fetchApi<Run[]>(`/runs/clients/${clientId}/runs`, { token }),

    get: (token: string, runId: string) =>
        fetchApi<Run>(`/runs/${runId}`, { token }),

    create: (token: string, clientId: string) =>
        fetchApi<Run>(`/runs/clients/${clientId}/runs`, {
            method: 'POST',
            token,
        }),

    getIssues: (token: string, runId: string) =>
        fetchApi<Issue[]>(`/runs/${runId}/issues`, { token }),

    getReports: (token: string, runId: string) =>
        fetchApi<Report[]>(`/runs/${runId}/reports`, { token }),
};

// Issues API
export const issuesApi = {
    list: (token: string, clientId: string) =>
        fetchApi<Issue[]>(`/issues/clients/${clientId}/issues`, { token }),

    updateStatus: (token: string, issueId: string, status: string) =>
        fetchApi<Issue>(`/issues/${issueId}`, {
            method: 'PATCH',
            body: JSON.stringify({ status }),
            token,
        }),
};

// Reports API
export const reportsApi = {
    get: (token: string, reportId: string) =>
        fetchApi<Report>(`/reports/${reportId}`, { token }),

    getMarkdown: async (token: string, reportId: string): Promise<string> => {
        const response = await fetch(`${API_URL}/reports/${reportId}/markdown`, {
            headers: { Authorization: `Bearer ${token}` },
        });
        return response.text();
    },

    downloadPdf: (token: string, reportId: string) =>
        `${API_URL}/reports/${reportId}/download?token=${token}`,
};

// Types
export interface User {
    id: string;
    org_id: string;
    email: string;
    role: 'admin' | 'staff';
    created_at: string;
}

export interface Client {
    id: string;
    org_id: string;
    name: string;
    gstin?: string;
    pan?: string;
    fy?: string;
    created_at: string;
}

export interface Document {
    id: string;
    org_id: string;
    client_id: string;
    type: 'bank' | 'invoice' | 'gst' | 'tds' | 'other';
    filename: string;
    status: 'pending' | 'processing' | 'processed' | 'failed';
    uploaded_at: string;
    meta?: Record<string, unknown>;
}

export interface Run {
    id: string;
    client_id: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    started_at?: string;
    ended_at?: string;
    metrics_json?: Record<string, unknown>;
    created_at: string;
}

export interface Issue {
    id: string;
    client_id: string;
    run_id: string;
    severity: 'low' | 'med' | 'high';
    category: 'missing_invoice' | 'duplicate' | 'mismatch' | 'gst_mismatch' | 'other';
    title: string;
    details_json?: Record<string, unknown>;
    status: 'open' | 'accepted' | 'resolved';
    created_at: string;
}

export interface Report {
    id: string;
    client_id: string;
    run_id: string;
    type: 'working_papers' | 'compliance_summary';
    content_md: string;
    content_pdf_url?: string;
    created_at: string;
}

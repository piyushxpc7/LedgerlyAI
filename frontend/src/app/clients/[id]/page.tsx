'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useDropzone } from 'react-dropzone';
import { useAuth } from '@/lib/auth';
import { clientsApi, documentsApi, runsApi, issuesApi, Client, Document, Run, Issue } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDate, formatDateTime, getStatusColor, getSeverityColor, getDocTypeLabel, getCategoryLabel } from '@/lib/utils';

export default function ClientDetailPage() {
    const { id } = useParams();
    const { token } = useAuth();
    const router = useRouter();

    const [client, setClient] = useState<Client | null>(null);
    const [documents, setDocuments] = useState<Document[]>([]);
    const [runs, setRuns] = useState<Run[]>([]);
    const [issues, setIssues] = useState<Issue[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isUploading, setIsUploading] = useState(false);
    const [isRunning, setIsRunning] = useState(false);
    const [activeTab, setActiveTab] = useState<'documents' | 'runs' | 'issues'>('documents');

    const clientId = id as string;

    useEffect(() => {
        if (token && clientId) {
            Promise.all([
                clientsApi.get(token, clientId),
                documentsApi.list(token, clientId),
                runsApi.list(token, clientId),
                issuesApi.list(token, clientId),
            ])
                .then(([clientData, docsData, runsData, issuesData]) => {
                    setClient(clientData);
                    setDocuments(docsData);
                    setRuns(runsData);
                    setIssues(issuesData);
                })
                .catch(console.error)
                .finally(() => setIsLoading(false));
        }
    }, [token, clientId]);

    const onDrop = useCallback(async (acceptedFiles: File[]) => {
        if (!token) return;

        setIsUploading(true);
        try {
            for (const file of acceptedFiles) {
                await documentsApi.upload(token, clientId, file, 'other');
            }
            // Refresh documents
            const docsData = await documentsApi.list(token, clientId);
            setDocuments(docsData);
        } catch (error) {
            console.error('Upload failed:', error);
        } finally {
            setIsUploading(false);
        }
    }, [token, clientId]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'application/pdf': ['.pdf'],
            'text/csv': ['.csv'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
        },
    });

    const startReconciliation = async () => {
        if (!token) return;

        setIsRunning(true);
        try {
            await runsApi.create(token, clientId);
            // Refresh runs
            const runsData = await runsApi.list(token, clientId);
            setRuns(runsData);
        } catch (error) {
            console.error('Failed to start reconciliation:', error);
        } finally {
            setIsRunning(false);
        }
    };

    const runIngestion = async (documentId: string) => {
        if (!token) return;

        try {
            await documentsApi.runIngestion(token, documentId);
            // Poll for status update
            setTimeout(async () => {
                const docsData = await documentsApi.list(token, clientId);
                setDocuments(docsData);
            }, 2000);
        } catch (error) {
            console.error('Failed to run ingestion:', error);
        }
    };

    const updateIssueStatus = async (issueId: string, status: string) => {
        if (!token) return;

        try {
            await issuesApi.updateStatus(token, issueId, status);
            const issuesData = await issuesApi.list(token, clientId);
            setIssues(issuesData);
        } catch (error) {
            console.error('Failed to update issue:', error);
        }
    };

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-pulse">Loading...</div>
            </div>
        );
    }

    if (!client) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div>Client not found</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            {/* Header */}
            <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        <div className="flex items-center space-x-4">
                            <Link href="/dashboard" className="text-primary hover:underline">
                                ← Dashboard
                            </Link>
                            <h1 className="text-xl font-bold">{client.name}</h1>
                        </div>
                        <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                            {client.gstin && <span>GSTIN: {client.gstin}</span>}
                            {client.pan && <span>PAN: {client.pan}</span>}
                            {client.fy && <span>FY: {client.fy}</span>}
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Actions */}
                <div className="flex justify-end mb-6 space-x-4">
                    <Button onClick={startReconciliation} disabled={isRunning || documents.length === 0}>
                        {isRunning ? 'Starting...' : '▶ Run Reconciliation'}
                    </Button>
                </div>

                {/* Tabs */}
                <div className="flex space-x-4 border-b mb-6">
                    {(['documents', 'runs', 'issues'] as const).map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${activeTab === tab
                                    ? 'border-primary text-primary'
                                    : 'border-transparent text-muted-foreground hover:text-foreground'
                                }`}
                        >
                            {tab.charAt(0).toUpperCase() + tab.slice(1)}
                            {tab === 'issues' && issues.filter(i => i.status === 'open').length > 0 && (
                                <span className="ml-2 bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                                    {issues.filter(i => i.status === 'open').length}
                                </span>
                            )}
                        </button>
                    ))}
                </div>

                {/* Documents Tab */}
                {activeTab === 'documents' && (
                    <div className="space-y-6">
                        {/* Upload Zone */}
                        <Card>
                            <CardContent className="p-6">
                                <div
                                    {...getRootProps()}
                                    className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${isDragActive
                                            ? 'border-primary bg-primary/5'
                                            : 'border-gray-300 dark:border-gray-600 hover:border-primary'
                                        }`}
                                >
                                    <input {...getInputProps()} />
                                    {isUploading ? (
                                        <p className="text-muted-foreground">Uploading...</p>
                                    ) : (
                                        <div>
                                            <p className="text-lg font-medium">
                                                {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
                                            </p>
                                            <p className="text-sm text-muted-foreground mt-1">
                                                or click to select files (PDF, CSV, XLSX)
                                            </p>
                                        </div>
                                    )}
                                </div>
                            </CardContent>
                        </Card>

                        {/* Documents List */}
                        <Card>
                            <CardHeader>
                                <CardTitle>Documents</CardTitle>
                                <CardDescription>Uploaded documents for this client</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {documents.length === 0 ? (
                                    <p className="text-center py-8 text-muted-foreground">
                                        No documents uploaded yet
                                    </p>
                                ) : (
                                    <div className="space-y-3">
                                        {documents.map((doc) => (
                                            <div
                                                key={doc.id}
                                                className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
                                            >
                                                <div>
                                                    <p className="font-medium">{doc.filename}</p>
                                                    <div className="flex items-center space-x-4 mt-1 text-sm text-muted-foreground">
                                                        <span>{getDocTypeLabel(doc.type)}</span>
                                                        <span>Uploaded {formatDateTime(doc.uploaded_at)}</span>
                                                    </div>
                                                </div>
                                                <div className="flex items-center space-x-4">
                                                    <Badge className={getStatusColor(doc.status)}>
                                                        {doc.status}
                                                    </Badge>
                                                    {doc.status === 'pending' && (
                                                        <Button size="sm" variant="outline" onClick={() => runIngestion(doc.id)}>
                                                            Process
                                                        </Button>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                )}

                {/* Runs Tab */}
                {activeTab === 'runs' && (
                    <Card>
                        <CardHeader>
                            <CardTitle>Reconciliation Runs</CardTitle>
                            <CardDescription>History of reconciliation processes</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {runs.length === 0 ? (
                                <p className="text-center py-8 text-muted-foreground">
                                    No reconciliation runs yet
                                </p>
                            ) : (
                                <div className="space-y-3">
                                    {runs.map((run) => (
                                        <Link
                                            key={run.id}
                                            href={`/runs/${run.id}`}
                                            className="block p-4 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                        >
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <p className="font-medium">Run {run.id.slice(0, 8)}...</p>
                                                    <div className="flex items-center space-x-4 mt-1 text-sm text-muted-foreground">
                                                        <span>Created {formatDateTime(run.created_at)}</span>
                                                        {run.ended_at && <span>Completed {formatDateTime(run.ended_at)}</span>}
                                                    </div>
                                                </div>
                                                <Badge className={getStatusColor(run.status)}>
                                                    {run.status}
                                                </Badge>
                                            </div>
                                        </Link>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                )}

                {/* Issues Tab */}
                {activeTab === 'issues' && (
                    <Card>
                        <CardHeader>
                            <CardTitle>Issues</CardTitle>
                            <CardDescription>Detected issues requiring attention</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {issues.length === 0 ? (
                                <p className="text-center py-8 text-muted-foreground">
                                    No issues found
                                </p>
                            ) : (
                                <div className="space-y-3">
                                    {issues.map((issue) => (
                                        <div
                                            key={issue.id}
                                            className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
                                        >
                                            <div className="flex items-start justify-between">
                                                <div className="flex-1">
                                                    <div className="flex items-center space-x-3">
                                                        <Badge className={getSeverityColor(issue.severity)}>
                                                            {issue.severity.toUpperCase()}
                                                        </Badge>
                                                        <Badge variant="outline">
                                                            {getCategoryLabel(issue.category)}
                                                        </Badge>
                                                    </div>
                                                    <p className="font-medium mt-2">{issue.title}</p>
                                                    <p className="text-sm text-muted-foreground mt-1">
                                                        {formatDateTime(issue.created_at)}
                                                    </p>
                                                </div>
                                                <div className="flex items-center space-x-2">
                                                    <Badge className={getStatusColor(issue.status)}>
                                                        {issue.status}
                                                    </Badge>
                                                    {issue.status === 'open' && (
                                                        <div className="flex space-x-2">
                                                            <Button
                                                                size="sm"
                                                                variant="outline"
                                                                onClick={() => updateIssueStatus(issue.id, 'accepted')}
                                                            >
                                                                Accept
                                                            </Button>
                                                            <Button
                                                                size="sm"
                                                                variant="outline"
                                                                onClick={() => updateIssueStatus(issue.id, 'resolved')}
                                                            >
                                                                Resolve
                                                            </Button>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                )}
            </main>
        </div>
    );
}

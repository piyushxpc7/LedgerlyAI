'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import { useAuth } from '@/lib/auth';
import { runsApi, reportsApi, Run, Issue, Report } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDateTime, getStatusColor, getSeverityColor, getCategoryLabel } from '@/lib/utils';

export default function RunDetailPage() {
    const { id } = useParams();
    const { token } = useAuth();

    const [run, setRun] = useState<Run | null>(null);
    const [issues, setIssues] = useState<Issue[]>([]);
    const [reports, setReports] = useState<Report[]>([]);
    const [selectedReport, setSelectedReport] = useState<Report | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const runId = id as string;

    useEffect(() => {
        if (token && runId) {
            Promise.all([
                runsApi.get(token, runId),
                runsApi.getIssues(token, runId),
                runsApi.getReports(token, runId),
            ])
                .then(([runData, issuesData, reportsData]) => {
                    setRun(runData);
                    setIssues(issuesData);
                    setReports(reportsData);
                    if (reportsData.length > 0) {
                        setSelectedReport(reportsData[0]);
                    }
                })
                .catch(console.error)
                .finally(() => setIsLoading(false));
        }
    }, [token, runId]);

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-pulse">Loading...</div>
            </div>
        );
    }

    if (!run) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div>Run not found</div>
            </div>
        );
    }

    const metrics = (run.metrics_json || {}) as Record<string, number>;

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            {/* Header */}
            <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        <div className="flex items-center space-x-4">
                            <Link href={`/clients/${run.client_id}`} className="text-primary hover:underline">
                                ← Back to Client
                            </Link>
                            <h1 className="text-xl font-bold">Reconciliation Run</h1>
                        </div>
                        <Badge className={getStatusColor(run.status)}>
                            {run.status}
                        </Badge>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Metrics */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                    <Card>
                        <CardHeader className="pb-2">
                            <CardDescription>Bank Transactions</CardDescription>
                            <CardTitle className="text-2xl">{metrics.bank_transactions || 0}</CardTitle>
                        </CardHeader>
                    </Card>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardDescription>Invoices</CardDescription>
                            <CardTitle className="text-2xl">{metrics.invoice_transactions || 0}</CardTitle>
                        </CardHeader>
                    </Card>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardDescription>Matched</CardDescription>
                            <CardTitle className="text-2xl text-green-600">{metrics.matched_count || 0}</CardTitle>
                        </CardHeader>
                    </Card>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardDescription>Issues</CardDescription>
                            <CardTitle className="text-2xl text-red-600">{issues.length}</CardTitle>
                        </CardHeader>
                    </Card>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Issues */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Issues Detected</CardTitle>
                            <CardDescription>{issues.length} issues found</CardDescription>
                        </CardHeader>
                        <CardContent className="max-h-96 overflow-y-auto">
                            {issues.length === 0 ? (
                                <p className="text-center py-8 text-muted-foreground">
                                    ✅ No issues detected
                                </p>
                            ) : (
                                <div className="space-y-3">
                                    {issues.map((issue) => (
                                        <div
                                            key={issue.id}
                                            className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                                        >
                                            <div className="flex items-center space-x-2 mb-1">
                                                <Badge className={getSeverityColor(issue.severity)}>
                                                    {issue.severity}
                                                </Badge>
                                                <Badge variant="outline" className="text-xs">
                                                    {getCategoryLabel(issue.category)}
                                                </Badge>
                                            </div>
                                            <p className="text-sm">{issue.title}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Reports */}
                    <Card>
                        <CardHeader>
                            <div className="flex justify-between items-center">
                                <div>
                                    <CardTitle>Reports</CardTitle>
                                    <CardDescription>Generated reports</CardDescription>
                                </div>
                                {selectedReport && token && (
                                    <a
                                        href={reportsApi.downloadPdf(token, selectedReport.id)}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        <Button variant="outline" size="sm">
                                            📄 Download PDF
                                        </Button>
                                    </a>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent>
                            {reports.length === 0 ? (
                                <p className="text-center py-8 text-muted-foreground">
                                    No reports generated yet
                                </p>
                            ) : (
                                <div className="space-y-4">
                                    {/* Report Tabs */}
                                    <div className="flex space-x-2">
                                        {reports.map((report) => (
                                            <Button
                                                key={report.id}
                                                variant={selectedReport?.id === report.id ? 'default' : 'outline'}
                                                size="sm"
                                                onClick={() => setSelectedReport(report)}
                                            >
                                                {report.type === 'working_papers' ? 'Working Papers' : 'Compliance Summary'}
                                            </Button>
                                        ))}
                                    </div>

                                    {/* Report Content */}
                                    {selectedReport && (
                                        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 max-h-96 overflow-y-auto prose dark:prose-invert prose-sm max-w-none markdown-content">
                                            <ReactMarkdown>{selectedReport.content_md}</ReactMarkdown>
                                        </div>
                                    )}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Timeline */}
                <Card className="mt-8">
                    <CardHeader>
                        <CardTitle>Timeline</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4 text-sm">
                            <div className="flex items-center space-x-4">
                                <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                                <span>Created: {formatDateTime(run.created_at)}</span>
                            </div>
                            {run.started_at && (
                                <div className="flex items-center space-x-4">
                                    <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                                    <span>Started: {formatDateTime(run.started_at)}</span>
                                </div>
                            )}
                            {run.ended_at && (
                                <div className="flex items-center space-x-4">
                                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                                    <span>Completed: {formatDateTime(run.ended_at)}</span>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </main>
        </div>
    );
}

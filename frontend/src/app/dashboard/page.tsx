'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { clientsApi, Client } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDate } from '@/lib/utils';

export default function DashboardPage() {
    const { user, token, logout, isLoading: authLoading } = useAuth();
    const [clients, setClients] = useState<Client[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        if (!authLoading && !user) {
            router.push('/login');
        }
    }, [user, authLoading, router]);

    useEffect(() => {
        if (token) {
            clientsApi.list(token)
                .then(setClients)
                .catch(console.error)
                .finally(() => setIsLoading(false));
        }
    }, [token]);

    if (authLoading || !user) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-pulse">Loading...</div>
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
                            <h1 className="text-xl font-bold text-primary">Ledgerly</h1>
                            <Badge variant="outline" className="text-xs">
                                {user.role.toUpperCase()}
                            </Badge>
                        </div>
                        <div className="flex items-center space-x-4">
                            <span className="text-sm text-muted-foreground">{user.email}</span>
                            <Button variant="outline" size="sm" onClick={logout}>
                                Logout
                            </Button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                            Dashboard
                        </h2>
                        <p className="text-muted-foreground mt-1">
                            Manage your clients and reconciliation workflows
                        </p>
                    </div>
                    <Link href="/clients/new">
                        <Button>+ Add Client</Button>
                    </Link>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    <Card>
                        <CardHeader className="pb-2">
                            <CardDescription>Total Clients</CardDescription>
                            <CardTitle className="text-3xl">{clients.length}</CardTitle>
                        </CardHeader>
                    </Card>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardDescription>Active Reconciliations</CardDescription>
                            <CardTitle className="text-3xl">-</CardTitle>
                        </CardHeader>
                    </Card>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardDescription>Open Issues</CardDescription>
                            <CardTitle className="text-3xl">-</CardTitle>
                        </CardHeader>
                    </Card>
                </div>

                {/* Clients List */}
                <Card>
                    <CardHeader>
                        <CardTitle>Clients</CardTitle>
                        <CardDescription>
                            Your organization's client portfolio
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {isLoading ? (
                            <div className="text-center py-8 text-muted-foreground">
                                Loading clients...
                            </div>
                        ) : clients.length === 0 ? (
                            <div className="text-center py-8">
                                <p className="text-muted-foreground mb-4">No clients yet</p>
                                <Link href="/clients/new">
                                    <Button>Add Your First Client</Button>
                                </Link>
                            </div>
                        ) : (
                            <div className="divide-y divide-gray-200 dark:divide-gray-700">
                                {clients.map((client) => (
                                    <Link
                                        key={client.id}
                                        href={`/clients/${client.id}`}
                                        className="block py-4 hover:bg-gray-50 dark:hover:bg-gray-800 -mx-6 px-6 transition-colors"
                                    >
                                        <div className="flex justify-between items-center">
                                            <div>
                                                <h3 className="font-medium text-gray-900 dark:text-gray-100">
                                                    {client.name}
                                                </h3>
                                                <div className="flex space-x-4 text-sm text-muted-foreground mt-1">
                                                    {client.gstin && <span>GSTIN: {client.gstin}</span>}
                                                    {client.pan && <span>PAN: {client.pan}</span>}
                                                    {client.fy && <span>FY: {client.fy}</span>}
                                                </div>
                                            </div>
                                            <div className="text-sm text-muted-foreground">
                                                Added {formatDate(client.created_at)}
                                            </div>
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Footer Disclaimer */}
                <div className="mt-8 text-center text-xs text-muted-foreground">
                    <p>
                        ⚠️ <strong>Disclaimer:</strong> Ledgerly is a preparation & workflow automation tool.
                        It does NOT file tax returns, certify documents, or provide legal opinions.
                    </p>
                </div>
            </main>
        </div>
    );
}

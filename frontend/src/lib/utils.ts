import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export function formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });
}

export function formatDateTime(dateString: string): string {
    return new Date(dateString).toLocaleString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

export function formatCurrency(amount: number): string {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 2,
    }).format(amount);
}

export function getSeverityColor(severity: string): string {
    switch (severity) {
        case 'high':
            return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30';
        case 'med':
            return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30';
        case 'low':
            return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30';
        default:
            return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900/30';
    }
}

export function getStatusColor(status: string): string {
    switch (status) {
        case 'pending':
            return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30';
        case 'processing':
        case 'running':
            return 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30';
        case 'processed':
        case 'completed':
            return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30';
        case 'failed':
            return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30';
        case 'open':
            return 'text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900/30';
        case 'accepted':
            return 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30';
        case 'resolved':
            return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30';
        default:
            return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900/30';
    }
}

export function getCategoryLabel(category: string): string {
    const labels: Record<string, string> = {
        missing_invoice: 'Missing Invoice',
        duplicate: 'Duplicate',
        mismatch: 'Mismatch',
        gst_mismatch: 'GST Mismatch',
        other: 'Other',
    };
    return labels[category] || category;
}

export function getDocTypeLabel(type: string): string {
    const labels: Record<string, string> = {
        bank: 'Bank Statement',
        invoice: 'Invoice',
        gst: 'GST Return',
        tds: 'TDS',
        other: 'Other',
    };
    return labels[type] || type;
}

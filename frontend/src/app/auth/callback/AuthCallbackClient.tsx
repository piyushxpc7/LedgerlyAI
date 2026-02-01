'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { TOKEN_KEY } from '@/lib/auth';

export default function AuthCallbackClient() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [error, setError] = useState('');

    useEffect(() => {
        const token = searchParams.get('token');
        if (token) {
            localStorage.setItem(TOKEN_KEY, token);
            document.cookie = `token=${token}; path=/; max-age=604800; SameSite=Lax`;
            router.push('/dashboard');
        } else {
            setError('Authentication failed. No token received.');
            setTimeout(() => {
                router.push('/login');
            }, 3000);
        }
    }, [router, searchParams]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="text-center">
                {error ? (
                    <>
                        <h2 className="text-2xl font-bold text-red-600 mb-2">Error</h2>
                        <p className="text-gray-600">{error}</p>
                    </>
                ) : (
                    <>
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
                        <h2 className="text-xl font-semibold text-gray-700">Completing sign in...</h2>
                    </>
                )}
            </div>
        </div>
    );
}

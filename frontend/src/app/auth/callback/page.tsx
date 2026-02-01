import { Suspense } from 'react';
import AuthCallbackClient from './AuthCallbackClient';

export default function AuthCallbackPage() {
    return (
        <Suspense
            fallback={
                <div className="min-h-screen flex items-center justify-center bg-gray-50">
                    <div className="text-center">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
                        <h2 className="text-xl font-semibold text-gray-700">Completing sign in...</h2>
                    </div>
                </div>
            }
        >
            <AuthCallbackClient />
        </Suspense>
    );
}

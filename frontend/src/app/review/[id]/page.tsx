'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getDocumentById, Document } from '@/lib/api';
import ReviewInterface from '@/components/ReviewInterface';
import Link from 'next/link';
import { ArrowLeft, Loader2, AlertCircle } from 'lucide-react';

export default function ReviewPage() {
    const params = useParams();
    const router = useRouter();
    const id = params?.id as string;

    const [document, setDocument] = useState<Document | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        if (!id) return;
        getDocumentById(id)
            .then(setDocument)
            .catch((err) => {
                const status = err?.response?.status;
                if (status === 401 || status === 403) {
                    router.push('/login');
                } else if (status === 404) {
                    setError('Document not found.');
                } else {
                    setError(err?.response?.data?.detail || 'Failed to load document. Is the backend running?');
                }
            })
            .finally(() => setIsLoading(false));
    }, [id, router]);

    // ── Loading state ──────────────────────────────────────────────────────────
    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="flex flex-col items-center gap-3 text-gray-500">
                    <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
                    <p className="text-sm">Loading document...</p>
                </div>
            </div>
        );
    }

    // ── Error state ────────────────────────────────────────────────────────────
    if (error || !document) {
        return (
            <div className="min-h-screen flex items-center justify-center p-6 bg-gray-50">
                <div className="p-8 bg-white rounded-2xl shadow-sm border border-red-100 text-center max-w-md">
                    <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <AlertCircle className="w-6 h-6 text-red-500" />
                    </div>
                    <h2 className="text-lg font-bold text-gray-900 mb-2">Error Loading Document</h2>
                    <p className="text-gray-500 text-sm mb-6">{error || 'The requested document could not be found.'}</p>
                    <Link
                        href="/"
                        className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-800"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Return to Dashboard
                    </Link>
                </div>
            </div>
        );
    }

    // ── Success state ──────────────────────────────────────────────────────────
    return (
        <div className="min-h-screen bg-gray-50 p-6 flex flex-col font-sans">
            <div className="max-w-[1600px] mx-auto w-full flex-1 flex flex-col">
                <header className="mb-6 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link
                            href="/"
                            className="p-2 hover:bg-gray-200 rounded-full transition-colors text-gray-600"
                            aria-label="Back to dashboard"
                        >
                            <ArrowLeft className="w-5 h-5" />
                        </Link>
                        <div>
                            <h1 className="text-xl font-bold text-gray-900">Document Review</h1>
                            <p className="text-sm text-gray-500">
                                Review and correct extracted AI data before final approval.
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className={`px-3 py-1 rounded-full text-xs font-semibold 
                            ${document.status.toUpperCase() === 'HITL_REVIEW' ? 'bg-yellow-100 text-yellow-700' :
                                document.status.toUpperCase() === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                                    document.status.toUpperCase() === 'FAILED' ? 'bg-red-100 text-red-700' :
                                        'bg-blue-100 text-blue-700'}`}>
                            {document.status.replace(/_/g, ' ')}
                        </div>
                        <div className="text-sm font-medium px-3 py-1 bg-gray-100 text-gray-700 rounded-full font-mono">
                            {document.id.split('-')[0]}...
                        </div>
                    </div>
                </header>

                <main className="flex-1">
                    <ReviewInterface document={document} />
                </main>
            </div>
        </div>
    );
}

'use client';

import { useState, useRef } from 'react';
import { uploadDocument } from '@/lib/api';
import { Upload, Loader2, CheckCircle2, XCircle } from 'lucide-react';

interface UploadButtonProps {
    onSuccess?: () => void;
}

export default function UploadButton({ onSuccess }: UploadButtonProps) {
    const [isUploading, setIsUploading] = useState(false);
    const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const [errorMsg, setErrorMsg] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        setStatus('idle');
        setErrorMsg('');

        try {
            await uploadDocument(file);
            setStatus('success');
            setTimeout(() => setStatus('idle'), 3000);
            onSuccess?.();
        } catch (error: any) {
            console.error('Upload failed', error);
            const detail = error?.response?.data?.detail || 'Upload failed. Please try again.';
            setErrorMsg(detail);
            setStatus('error');
            setTimeout(() => { setStatus('idle'); setErrorMsg(''); }, 5000);
        } finally {
            setIsUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    return (
        <div className="relative flex flex-col items-end gap-1">
            <input
                type="file"
                className="hidden"
                ref={fileInputRef}
                onChange={handleUpload}
                accept="application/pdf,image/*,.pdf,.png,.jpg,.jpeg,.tiff,.bmp"
            />

            <button
                id="upload-invoice-btn"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all shadow-sm
                    ${status === 'idle' ? 'bg-blue-600 hover:bg-blue-700 text-white' : ''}
                    ${status === 'success' ? 'bg-green-100 text-green-700 border border-green-200' : ''}
                    ${status === 'error' ? 'bg-red-100 text-red-700 border border-red-200' : ''}
                    ${isUploading ? 'opacity-70 cursor-not-allowed' : ''}
                `}
            >
                {isUploading ? (
                    <><Loader2 className="w-4 h-4 animate-spin" />Uploading...</>
                ) : status === 'success' ? (
                    <><CheckCircle2 className="w-4 h-4" />Uploaded!</>
                ) : status === 'error' ? (
                    <><XCircle className="w-4 h-4" />Failed</>
                ) : (
                    <><Upload className="w-4 h-4" />Upload Invoice</>
                )}
            </button>

            {errorMsg && (
                <p className="text-xs text-red-600 max-w-xs text-right">{errorMsg}</p>
            )}
        </div>
    );
}

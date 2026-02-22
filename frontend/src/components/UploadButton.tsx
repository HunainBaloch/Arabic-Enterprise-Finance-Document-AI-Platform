"use client";

import { useState, useRef } from "react";
import { uploadDocument } from "@/lib/api";
import { Upload, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { useRouter } from "next/navigation";

export default function UploadButton() {
    const [isUploading, setIsUploading] = useState(false);
    const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const fileInputRef = useRef<HTMLInputElement>(null);
    const router = useRouter();

    const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        setStatus('idle');

        try {
            await uploadDocument(file);
            setStatus('success');
            setTimeout(() => setStatus('idle'), 3000);
            router.refresh();
        } catch (error) {
            console.error("Upload failed", error);
            setStatus('error');
            setTimeout(() => setStatus('idle'), 3000);
        } finally {
            setIsUploading(false);
            if (fileInputRef.current) {
                fileInputRef.current.value = "";
            }
        }
    };

    return (
        <div className="relative">
            <input
                type="file"
                className="hidden"
                ref={fileInputRef}
                onChange={handleUpload}
                accept="application/pdf,image/*"
            />

            <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className={`flex items-center gap-2 px-4 py-2 rounded-md font-medium text-sm transition-all shadow-sm
                    ${status === 'idle' ? 'bg-blue-600 hover:bg-blue-700 text-white' : ''}
                    ${status === 'success' ? 'bg-green-100 text-green-700 border border-green-200' : ''}
                    ${status === 'error' ? 'bg-red-100 text-red-700 border border-red-200' : ''}
                    ${isUploading ? 'opacity-70 cursor-not-allowed' : ''}
                `}
            >
                {isUploading ? (
                    <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Uploading...
                    </>
                ) : status === 'success' ? (
                    <>
                        <CheckCircle2 className="w-4 h-4" />
                        Uploaded!
                    </>
                ) : status === 'error' ? (
                    <>
                        <XCircle className="w-4 h-4" />
                        Failed
                    </>
                ) : (
                    <>
                        <Upload className="w-4 h-4" />
                        Upload Invoice
                    </>
                )}
            </button>
        </div>
    );
}

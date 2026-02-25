"use client";

import { useEffect, useState } from "react";
import { Document, updateDocumentStatus, api } from "@/lib/api";
import { AlertCircle, Check, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";

export default function ReviewInterface({ document }: { document: Document }) {
    const router = useRouter();
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Initialize form state with extracted LLM data if available
    const initialData = document.extracted_data?.llm_output || {};
    const [formData, setFormData] = useState({
        vendor_name: initialData.vendor_name || "",
        trn: initialData.trn || "",
        invoice_date: initialData.invoice_date || "",
        total_amount: initialData.total_amount || "",
        vat_amount: initialData.vat_amount || "",
    });

    const [fileUrl, setFileUrl] = useState<string | null>(null);
    const [isFetchingFile, setIsFetchingFile] = useState(false);

    useEffect(() => {
        const fetchFile = async () => {
            setIsFetchingFile(true);
            try {
                const response = await api.get(`documents/${document.id}/file`, {
                    responseType: 'blob'
                });
                const url = URL.createObjectURL(response.data);
                setFileUrl(url);
            } catch (error) {
                console.error("Failed to fetch document file", error);
            } finally {
                setIsFetchingFile(false);
            }
        };

        fetchFile();
        return () => {
            if (fileUrl) URL.revokeObjectURL(fileUrl);
        };
    }, [document.id]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleApprove = async () => {
        setIsSubmitting(true);
        try {
            // Merge human corrections back into the extracted data object
            const updatedData = {
                ...document.extracted_data,
                llm_output: formData, // the corrected data
                human_reviewed: true
            };

            await updateDocumentStatus(document.id, "COMPLETED", updatedData);
            window.location.href = "/";
        } catch (error) {
            console.error("Failed to approve document", error);
            alert("Failed to submit approval.");
        } finally {
            setIsSubmitting(false);
        }
    };

    const vatValid = document.extracted_data?.llm_output?.vat_validation?.is_valid;
    const confidence = document.confidence_score ? (document.confidence_score * 100).toFixed(1) : 0;

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-[calc(100vh-140px)]">
            {/* Left Column: Image Viewer */}
            <div className="bg-gray-100 rounded-lg border border-gray-200 overflow-hidden flex flex-col">
                <div className="p-3 border-b bg-white flex justify-between items-center text-sm font-medium text-gray-700 shadow-sm z-10">
                    <span>Original Document</span>
                    <span className="text-gray-400 font-mono text-xs">{document.filename}</span>
                </div>
                <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-gray-50/50 relative">
                    {isFetchingFile ? (
                        <div className="flex flex-col items-center gap-2">
                            <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                            <p className="text-xs text-gray-400">Loading file...</p>
                        </div>
                    ) : fileUrl ? (
                        document.mime_type === "application/pdf" ? (
                            <embed
                                src={fileUrl}
                                type="application/pdf"
                                className="w-full h-full rounded shadow-sm"
                            />
                        ) : (
                            <img
                                src={fileUrl}
                                alt="Document Scan"
                                className="max-w-full max-h-full object-contain rounded shadow-sm"
                            />
                        )
                    ) : (
                        <div className="text-center p-6">
                            <AlertCircle className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                            <p className="text-sm text-gray-400">Could not load document file</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Right Column: Form Editor */}
            <div className="bg-white rounded-lg border border-gray-200 flex flex-col shadow-sm">
                <div className="p-4 border-b bg-gray-50 flex justify-between items-center">
                    <div>
                        <h2 className="font-semibold text-gray-900">Extracted Data</h2>
                        <p className="text-xs text-gray-500 mt-1">Confidence Score: <span className="font-medium">{confidence}%</span></p>
                    </div>
                    <div className={`px-2 py-1 rounded text-xs font-semibold ${vatValid ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {vatValid ? "VAT Math Valid" : "VAT Math Invalid"}
                    </div>
                </div>

                <div className="flex-1 p-6 overflow-y-auto space-y-5">
                    {[
                        { label: "Vendor Name", name: "vendor_name", type: "text" },
                        { label: "TRN Number", name: "trn", type: "text" },
                        { label: "Invoice Date", name: "invoice_date", type: "date" },
                        { label: "Total Amount", name: "total_amount", type: "number", step: "0.01" },
                        { label: "VAT Amount (5%)", name: "vat_amount", type: "number", step: "0.01" },
                    ].map((field) => {
                        const isLowConfidence = initialData.low_confidence_fields?.includes(field.name);
                        return (
                            <div key={field.name} className="relative">
                                <label className={`block text-sm font-medium mb-1 ${isLowConfidence ? 'text-red-700' : 'text-gray-700'}`}>
                                    {field.label} {isLowConfidence && <span className="text-red-500 text-xs ml-2">(Low Confidence)</span>}
                                </label>
                                <input
                                    type={field.type}
                                    name={field.name}
                                    step={field.step}
                                    value={formData[field.name as keyof typeof formData]}
                                    onChange={handleChange}
                                    className={`w-full rounded-md shadow-sm sm:text-sm px-3 py-2 border bg-white transition-colors focus:ring-blue-500 focus:border-blue-500 
                                ${isLowConfidence ? 'border-red-500 text-red-900 bg-red-50 focus:ring-red-500 focus:border-red-500' : 'border-gray-300 text-gray-900'}`}
                                />
                            </div>
                        )
                    })}

                    {/* Reasoning Alert */}
                    {initialData.reasoning && (
                        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-md p-4 text-sm text-blue-800">
                            <span className="font-semibold block mb-1">AI Reasoning:</span>
                            {initialData.reasoning}
                        </div>
                    )}
                </div>

                <div className="p-4 border-t bg-gray-50 flex justify-end gap-3 rounded-b-lg">
                    <button
                        type="button"
                        onClick={() => router.push("/")}
                        disabled={isSubmitting}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 shadow-sm transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        onClick={handleApprove}
                        disabled={isSubmitting}
                        className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
                    >
                        {isSubmitting ? (
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                            <Check className="w-4 h-4 mr-2" />
                        )}
                        Approve & Save
                    </button>
                </div>
            </div>
        </div>
    );
}

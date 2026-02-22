import Link from "next/link";
import { FileText, CheckCircle, AlertTriangle, Clock } from "lucide-react";
import { Document } from "@/lib/api";

export default function DocumentList({ documents }: { documents: Document[] }) {
    const getStatusIcon = (status: string) => {
        if (status === "COMPLETED") return <CheckCircle className="text-green-500 w-5 h-5" />;
        if (status === "HITL_REVIEW") return <AlertTriangle className="text-yellow-500 w-5 h-5" />;
        return <Clock className="text-gray-500 w-5 h-5" />;
    };

    return (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 text-sm translate-z-0">
                <thead className="bg-gray-50">
                    <tr>
                        <th className="px-6 py-4 text-left font-medium text-gray-500">Document</th>
                        <th className="px-6 py-4 text-left font-medium text-gray-500">Date Added</th>
                        <th className="px-6 py-4 text-left font-medium text-gray-500">Status</th>
                        <th className="px-6 py-4 text-right font-medium text-gray-500">Action</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                    {documents.map((doc) => (
                        <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
                            <td className="px-6 py-4">
                                <div className="flex items-center gap-3">
                                    <FileText className="text-blue-500 w-5 h-5" />
                                    <span className="font-medium text-gray-900">{doc.filename}</span>
                                </div>
                            </td>
                            <td className="px-6 py-4 text-gray-500">
                                {new Date(doc.created_at).toLocaleDateString()}
                            </td>
                            <td className="px-6 py-4">
                                <div className="flex items-center gap-2">
                                    {getStatusIcon(doc.status)}
                                    <span className="capitalize">{doc.status.replace("_", " ").toLowerCase()}</span>
                                </div>
                            </td>
                            <td className="px-6 py-4 text-right">
                                <Link
                                    href={`/review/${doc.id}`}
                                    className="inline-flex items-center px-4 py-2 bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 transition-colors font-medium text-sm"
                                >
                                    {doc.status === "HITL_REVIEW" ? "Review Required" : "View Details"}
                                </Link>
                            </td>
                        </tr>
                    ))}
                    {documents.length === 0 && (
                        <tr>
                            <td colSpan={4} className="px-6 py-12 text-center text-gray-500">
                                No documents found. Upload some invoices to get started.
                            </td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>
    );
}

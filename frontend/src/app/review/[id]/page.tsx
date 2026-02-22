import { getDocumentById } from "@/lib/api";
import ReviewInterface from "@/components/ReviewInterface";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default async function ReviewPage({
    params,
}: {
    params: { id: string };
}) {
    try {
        const document = await getDocumentById(params.id);

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
                        <div className="text-sm font-medium px-3 py-1 bg-blue-100 text-blue-800 rounded-full">
                            ID: {document.id.split("-")[0]}...
                        </div>
                    </header>

                    <main className="flex-1">
                        <ReviewInterface document={document} />
                    </main>
                </div>
            </div>
        );
    } catch (error) {
        return (
            <div className="min-h-screen flex items-center justify-center p-6 bg-gray-50">
                <div className="p-8 bg-white rounded-lg shadow-sm border border-red-100 text-center max-w-md">
                    <h2 className="text-lg font-bold text-red-600 mb-2">Error Loading Document</h2>
                    <p className="text-gray-600 mb-6">The requested document could not be found or the API is unreachable.</p>
                    <Link
                        href="/"
                        className="inline-flex items-center text-sm font-medium text-blue-600 hover:text-blue-800"
                    >
                        <ArrowLeft className="w-4 h-4 mr-2" />
                        Return to Dashboard
                    </Link>
                </div>
            </div>
        );
    }
}

import { getAllDocuments } from "@/lib/api";
import DocumentList from "@/components/DocumentList";
import UploadButton from "@/components/UploadButton";

export const dynamic = "force-dynamic";

export default async function Home() {
  const documents = await getAllDocuments().catch(() => []);

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans antialiased p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-center justify-between border-b border-gray-200 pb-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">
              Finance Document AI Workspace
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              Review and manage extracted UAE VAT invoices
            </p>
          </div>
          <UploadButton />
        </header>

        <main>
          <DocumentList documents={documents} />
        </main>
      </div>
    </div>
  );
}

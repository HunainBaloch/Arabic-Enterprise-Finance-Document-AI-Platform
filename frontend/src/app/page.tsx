'use client';

import { useEffect, useState } from 'react';
import { getAllDocuments, Document } from '@/lib/api';
import DocumentList from '@/components/DocumentList';
import UploadButton from '@/components/UploadButton';
import { useAuth } from '@/lib/AuthProvider';
import { LogOut, RefreshCw, FileText, Activity } from 'lucide-react';

export default function Home() {
  const { isAuthenticated, logout } = useAuth();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  const fetchDocuments = async (showRefresh = false) => {
    if (showRefresh) setIsRefreshing(true);
    try {
      const docs = await getAllDocuments();
      setDocuments(docs);
    } catch {
      // 401 will be handled by the global axios interceptor → redirect to login
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    setIsMounted(true);
    if (isAuthenticated) {
      fetchDocuments();
    }
  }, [isAuthenticated]);

  // Auto-polling for documents that are processing
  useEffect(() => {
    if (!isAuthenticated) return;

    const hasProcessing = documents.some(d => !['COMPLETED', 'HITL_REVIEW', 'FAILED'].includes(d.status.toUpperCase()));
    if (hasProcessing) {
      const interval = setInterval(() => {
        fetchDocuments(false); // Silent fetch
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [isAuthenticated, documents]);

  const handleUploadSuccess = () => {
    fetchDocuments(true);
  };

  const pendingCount = documents.filter(d => d.status.toUpperCase() === 'HITL_REVIEW').length;
  const completedCount = documents.filter(d => d.status.toUpperCase() === 'COMPLETED').length;
  const processingCount = documents.filter(d => !['COMPLETED', 'HITL_REVIEW', 'FAILED'].includes(d.status.toUpperCase())).length;

  if (!isMounted || !isAuthenticated) return null; // Wait for mount and auth

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      {/* Top navbar */}
      <nav className="bg-white border-b border-gray-200 px-8 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <FileText className="w-4 h-4 text-white" />
          </div>
          <div>
            <span className="font-bold text-gray-900 text-sm">Finance Document AI</span>
            <span className="text-xs text-gray-400 ml-2">Arabic Enterprise Platform</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            id="refresh-btn"
            onClick={() => fetchDocuments(true)}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg text-sm transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            id="logout-btn"
            onClick={logout}
            className="flex items-center gap-1.5 px-3 py-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg text-sm transition-all"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign out
          </button>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-8 py-8 space-y-6">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">Finance Document Workspace</h1>
            <p className="text-sm text-gray-500 mt-1">Review and manage extracted UAE VAT invoices</p>
          </div>
          <UploadButton onSuccess={handleUploadSuccess} />
        </div>

        {/* Stats cards */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-gray-500">Total Documents</p>
              <Activity className="w-4 h-4 text-blue-500" />
            </div>
            <p className="text-3xl font-bold text-gray-900 mt-2">{documents.length}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-gray-500">Needs Review</p>
              <span className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
            </div>
            <p className="text-3xl font-bold text-yellow-600 mt-2">{pendingCount}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-gray-500">Completed</p>
              <span className="w-2 h-2 rounded-full bg-green-400" />
            </div>
            <p className="text-3xl font-bold text-green-600 mt-2">{completedCount}</p>
          </div>
        </div>

        {/* Document table */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
              <p className="text-sm text-gray-500">Loading documents...</p>
            </div>
          ) : (
            <DocumentList documents={documents} />
          )}
        </div>
      </div>
    </div>
  );
}

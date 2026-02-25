'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { login } from '@/lib/api';
import { FileText, Lock, Mail, AlertCircle, Loader2 } from 'lucide-react';

export default function LoginPage() {
    const router = useRouter();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);
        try {
            await login(email, password);
            router.push('/');
        } catch (err: any) {
            const msg = err?.response?.data?.detail || 'Invalid email or password.';
            setError(msg);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
            {/* Glowing orbs */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/20 rounded-full blur-3xl animate-pulse" />
                <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-indigo-600/15 rounded-full blur-3xl animate-pulse delay-1000" />
            </div>

            <div className="relative w-full max-w-md">
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600/20 border border-blue-500/30 rounded-2xl mb-4 backdrop-blur-sm">
                        <FileText className="w-8 h-8 text-blue-400" />
                    </div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Finance Document AI</h1>
                    <p className="text-slate-400 mt-2 text-sm">Arabic Enterprise Platform — Sign in to continue</p>
                </div>

                {/* Card */}
                <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl">
                    <form onSubmit={handleSubmit} className="space-y-5">
                        {/* Email */}
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">Email address</label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                <input
                                    id="email"
                                    type="email"
                                    required
                                    autoComplete="email"
                                    value={email}
                                    onChange={e => setEmail(e.target.value)}
                                    placeholder="admin@test.com"
                                    className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-sm transition-all"
                                />
                            </div>
                        </div>

                        {/* Password */}
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">Password</label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                <input
                                    id="password"
                                    type="password"
                                    required
                                    autoComplete="current-password"
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    placeholder="••••••••••"
                                    className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-sm transition-all"
                                />
                            </div>
                        </div>

                        {/* Error */}
                        {error && (
                            <div className="flex items-center gap-2.5 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
                                <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                                <p className="text-sm text-red-400">{error}</p>
                            </div>
                        )}

                        {/* Submit */}
                        <button
                            id="login-submit"
                            type="submit"
                            disabled={isLoading}
                            className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-xl transition-all duration-200 shadow-lg shadow-blue-600/25 text-sm mt-2"
                        >
                            {isLoading ? (
                                <><Loader2 className="w-4 h-4 animate-spin" /> Signing in...</>
                            ) : (
                                'Sign in'
                            )}
                        </button>
                    </form>

                    {/* Hint */}
                    <div className="mt-6 pt-5 border-t border-white/5">
                        <p className="text-xs text-slate-600 text-center">
                            Default: <span className="text-slate-500">admin@test.com</span> / <span className="text-slate-500">AdminPass123!</span>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

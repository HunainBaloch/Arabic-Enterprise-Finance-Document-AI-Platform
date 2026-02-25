'use client';

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { getToken, clearToken } from '@/lib/api';
import { useRouter, usePathname } from 'next/navigation';

interface AuthContextValue {
    isAuthenticated: boolean;
    logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
    isAuthenticated: false,
    logout: () => { },
});

export function AuthProvider({ children }: { children: ReactNode }) {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        const token = getToken();
        setIsAuthenticated(!!token);
        if (!token && pathname !== '/login') {
            router.push('/login');
        }
    }, [pathname, router]);

    const logout = useCallback(() => {
        clearToken();
        setIsAuthenticated(false);
        router.push('/login');
    }, [router]);

    return (
        <AuthContext.Provider value={{ isAuthenticated, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}

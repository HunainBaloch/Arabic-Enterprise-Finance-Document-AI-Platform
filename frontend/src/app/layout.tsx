import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/AuthProvider";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Finance Document AI — Arabic Enterprise Platform",
  description: "AI-powered Arabic finance document processing for UAE VAT invoices",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" dir="ltr">
      <body className={`${inter.variable} antialiased font-sans`}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}

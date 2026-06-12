import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";
import Providers from "@/components/shared/Providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Antigravity RAG | Enterprise AI Agent Assistant",
  description: "Advanced Multi-Agent RAG Assistant utilizing Hybrid Search, Cross-Encoders, and LLM orchestration.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased`}>
        <Providers>
          <div className="flex h-screen w-screen overflow-hidden bg-zinc-950 text-zinc-100">
            {/* Navigation Sidebar */}
            <Sidebar />

            {/* Page Main Content Area */}
            <main className="flex-1 flex flex-col h-screen overflow-hidden bg-zinc-900/10 relative">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}

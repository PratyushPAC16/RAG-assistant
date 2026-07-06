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
  title: "TalentMind AI | Enterprise AI Agent Assistant",
  description:
    "Advanced Multi-Agent RAG Assistant utilizing Hybrid Search, Cross-Encoders, and LLM orchestration.",
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
          <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground relative transition-colors duration-300">

            {/* ── Ambient Mesh Background ─────────────────────────────────── */}
            {/* Primary brand orb — top left */}
            <div
              className="absolute top-[-20%] left-[-10%] w-[55%] h-[55%] rounded-full pointer-events-none z-0 dark:opacity-[0.065] opacity-[0.03]"
              style={{
                background: "radial-gradient(ellipse, rgba(41,151,255,1) 0%, transparent 70%)",
                filter: "blur(120px)",
              }}
            />
            {/* Violet orb — bottom right */}
            <div
              className="absolute bottom-[-20%] right-[-10%] w-[65%] h-[65%] rounded-full pointer-events-none z-0 dark:opacity-[0.10] opacity-[0.02]"
              style={{
                background: "radial-gradient(ellipse, rgba(139,92,246,1) 0%, transparent 70%)",
                filter: "blur(150px)",
              }}
            />
            {/* Cool indigo — mid right */}
            <div
              className="absolute top-[15%] right-[20%] w-[45%] h-[45%] rounded-full pointer-events-none z-0 dark:opacity-[0.04] opacity-[0.01]"
              style={{
                background: "radial-gradient(ellipse, rgba(99,102,241,1) 0%, transparent 70%)",
                filter: "blur(130px)",
              }}
            />
            {/* Warm pink — lower left */}
            <div
              className="absolute bottom-[10%] left-[15%] w-[40%] h-[40%] rounded-full pointer-events-none z-0 dark:opacity-[0.03] opacity-[0.01]"
              style={{
                background: "radial-gradient(ellipse, rgba(214,91,180,1) 0%, transparent 70%)",
                filter: "blur(110px)",
              }}
            />
            {/* Subtle chromatic aberration center glow */}
            <div
              className="absolute top-[35%] left-[40%] w-[30%] h-[30%] rounded-full pointer-events-none z-0 dark:opacity-100 opacity-[0.15]"
              style={{
                background:
                  "conic-gradient(from 0deg, rgba(41,151,255,0.03), rgba(99,102,241,0.03), rgba(34,211,238,0.02), rgba(41,151,255,0.03))",
                filter: "blur(80px)",
              }}
            />

            {/* ── Navigation Sidebar ──────────────────────────────────────── */}
            <Sidebar />

            {/* ── Main Content Area ───────────────────────────────────────── */}
            <main
              className="flex-1 flex flex-col h-screen overflow-hidden relative z-10"
              style={{
                background: "var(--glass-fill-inset)",
                backdropFilter: "var(--glass-blur)",
                WebkitBackdropFilter: "var(--glass-blur)",
              }}
            >
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}

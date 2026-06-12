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
          <div className="flex h-screen w-screen overflow-hidden bg-[#11100F] text-white relative">
            {/* Layered ambient glows */}
            <div className="absolute top-[-15%] left-[-15%] w-[60%] h-[60%] rounded-full bg-[#D65BB4] opacity-[0.07] blur-[130px] pointer-events-none z-0" />
            <div className="absolute bottom-[-15%] right-[-15%] w-[70%] h-[70%] rounded-full bg-[#66415C] opacity-[0.15] blur-[160px] pointer-events-none z-0" />
            <div className="absolute top-[20%] right-[30%] w-[50%] h-[50%] rounded-full bg-[#66415C] opacity-[0.05] blur-[140px] pointer-events-none z-0" />
            <div className="absolute bottom-[20%] left-[20%] w-[45%] h-[45%] rounded-full bg-[#D65BB4] opacity-[0.04] blur-[120px] pointer-events-none z-0" />

            {/* Navigation Sidebar */}
            <Sidebar />

            {/* Page Main Content Area */}
            <main className="flex-1 flex flex-col h-screen overflow-hidden bg-[#1A171B]/35 backdrop-blur-2xl relative z-10">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}

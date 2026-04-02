import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const interFont = Inter({
  variable: "--font-inter",
  subsets: ["cyrillic", "latin"],
});

export const metadata: Metadata = {
  title: "Tomer AI - Голосовой помощник",
  description: "Learn Hebrew with voice AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" dir="ltr" className={`${interFont.variable} antialiased h-full`}>
      <body className="bg-white text-slate-900 min-h-full flex flex-col font-sans relative overflow-hidden">
        {children}
      </body>
    </html>
  );
}

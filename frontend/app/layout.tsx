import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Company Expert",
  description: "AI-powered knowledge base assistant",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-zinc-950 text-zinc-100 font-sans">{children}</body>
    </html>
  );
}

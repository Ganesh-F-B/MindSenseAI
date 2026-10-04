import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: {
    default: "MindSense AI - Empathetic AI Mental Health Companion",
    template: "%s | MindSense AI",
  },
  description: "Safe, confidential, and empathetic AI mental wellness companion providing 24/7 conversational support, emotion detection, and automated crisis assistance.",
  robots: {
    index: true,
    follow: true,
  },
  openGraph: {
    title: "MindSense AI - Empathetic AI Mental Health Companion",
    description: "Safe, confidential, and empathetic AI mental wellness companion providing 24/7 conversational support, emotion detection, and automated crisis assistance.",
    siteName: "MindSense AI",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-foreground min-h-screen font-sans">
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
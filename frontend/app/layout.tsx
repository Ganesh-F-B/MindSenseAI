import "./globals.css";
import { Providers } from "./providers";

export const metadata = {
  title: "MindSense AI",
  description: "AI Mental Health System",
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
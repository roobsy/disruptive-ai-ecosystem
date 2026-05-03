import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ecosystem · Disruptive Intelligence",
  description: "Autonomous Disruptive Intelligence Ecosystem",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}

import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Fragrance Collection Tracker",
  description: "Track and rank a personal fragrance collection.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

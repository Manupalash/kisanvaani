import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "KisanVaani — రైతు మాట, మన మాట", description: "A voice-first farm companion for Telugu farmers." };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="te"><body>{children}</body></html>;
}

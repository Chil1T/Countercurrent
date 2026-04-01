import type { Metadata } from "next";
import { Inter, Manrope } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-stitch-body",
  subsets: ["latin"],
});

const manrope = Manrope({
  variable: "--font-stitch-headline-var",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ReCurr",
  description: "Web product shell for the ReCurr blueprint-first pipeline.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      className={`${inter.variable} ${manrope.variable} h-full antialiased`}
    >
      <body suppressHydrationWarning className="min-h-full flex flex-col">
        {children}
      </body>
    </html>
  );
}

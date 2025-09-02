import "./globals.css";
import Providers from "./providers";

export const metadata = {
  title: "Papers",
  description: "Better than Zotero",
};

/**
 * Root layout applied to all pages. Wraps the application in Providers
 * and defines the html/body structure. The minimal background color
 * ensures content is readable on light mode.
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
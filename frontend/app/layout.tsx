import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "COUNCIL",
  description: "Argue real historical court cases against AI opponents backed by actual transcripts.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen relative">

        {/* Decorative pillar lines with cap ornaments */}
        <div className="pillar-left" aria-hidden />
        <div className="pillar-right" aria-hidden />

        {/* Top cornice — graduated gold band */}
        <div
          className="fixed top-0 left-0 right-0 z-50 pointer-events-none"
          aria-hidden
          style={{
            height: "3px",
            background: "linear-gradient(to right, transparent 0%, rgba(212,175,55,0.16) 10%, rgba(212,175,55,0.62) 50%, rgba(212,175,55,0.16) 90%, transparent 100%)",
          }}
        />

        {/* Faint architectural arch tracery — background atmosphere */}
        <div
          className="fixed top-0 left-1/2 -translate-x-1/2 pointer-events-none z-0 select-none"
          aria-hidden
          style={{ opacity: 0.05 }}
        >
          <svg width="700" height="360" viewBox="0 0 700 360" fill="none">
            <path
              d="M70 360 C70 140, 290 12, 350 12 C410 12, 630 140, 630 360"
              stroke="#d4af37" strokeWidth="1.5" fill="none"
            />
            <path
              d="M130 360 C130 176, 298 52, 350 52 C402 52, 570 176, 570 360"
              stroke="#d4af37" strokeWidth="1" fill="none"
            />
            <path
              d="M200 360 C200 218, 308 100, 350 100 C392 100, 500 218, 500 360"
              stroke="#d4af37" strokeWidth="0.5" fill="none"
            />
            {/* Keystone */}
            <polygon points="350,4 355,14 350,24 345,14" fill="#d4af37" />
          </svg>
        </div>

        {children}

        {/* Bottom frieze */}
        <div
          className="fixed bottom-0 left-0 right-0 h-px pointer-events-none z-50"
          aria-hidden
          style={{
            background: "linear-gradient(to right, transparent, rgba(212,175,55,0.16) 30%, rgba(212,175,55,0.16) 70%, transparent)",
          }}
        />
      </body>
    </html>
  );
}

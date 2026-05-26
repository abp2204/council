"use client";

import { motion } from "framer-motion";
import { Scale, BookOpen, Gavel, Shield, Landmark, ChevronRight } from "lucide-react";
import { useState } from "react";

const cases = [
  {
    id: "brown",
    title: "Brown v. Board of Education",
    area: "Constitutional Law",
    role: "Petitioner's Lead Counsel",
    desc: "A landmark challenge to racial segregation in public schools.",
  },
  {
    id: "gideon",
    title: "Gideon v. Wainwright",
    area: "Criminal Procedure",
    role: "Defense Attorney",
    desc: "The fundamental right to counsel for all criminal defendants.",
  }
];

export default function PrototypeLobby() {
  const [hoveredCase, setHoveredCase] = useState<string | null>(null);

  return (
    <div className="min-h-screen relative overflow-hidden flex flex-col items-center justify-center p-8 bg-charcoal">
      {/* Architectural Background Elements */}
      <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-b from-walnut-warm/20 to-transparent" />
      <div className="absolute bottom-0 left-0 w-full h-64 bg-gradient-to-t from-black to-transparent opacity-50" />
      
      {/* Abstract Pillars */}
      <div className="absolute left-10 top-0 bottom-0 w-1 bg-gradient-to-b from-gold-glow/0 via-gold-glow/20 to-gold-glow/0 hidden lg:block" />
      <div className="absolute right-10 top-0 bottom-0 w-1 bg-gradient-to-b from-gold-glow/0 via-gold-glow/20 to-gold-glow/0 hidden lg:block" />

      {/* Main Container */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="z-10 w-full max-w-4xl flex flex-col items-center"
      >
        {/* Wordmark */}
        <div className="flex flex-col items-center mb-16 text-center">
          <Landmark className="text-gold-glow w-12 h-12 mb-6" />
          <h1 className="text-6xl font-bold mb-4 tracking-widest text-white drop-shadow-md">
            COUNCIL
          </h1>
          <div className="h-0.5 w-24 bg-gold-glow mb-6" />
          <p className="legal-body text-xl text-ivory/70 max-w-2xl leading-relaxed italic">
            "Justice is the constant and perpetual will to allot to every man his due."
          </p>
        </div>

        {/* Case Selection */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full">
          {cases.map((c) => (
            <motion.div
              key={c.id}
              onMouseEnter={() => setHoveredCase(c.id)}
              onMouseLeave={() => setHoveredCase(null)}
              whileHover={{ scale: 1.02 }}
              className="group relative bg-walnut-deep/40 backdrop-blur-sm gold-border p-8 cursor-pointer overflow-hidden transition-all gold-glow-hover"
            >
              {/* Internal Accent */}
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-30 transition-opacity">
                <Scale size={48} />
              </div>

              <div className="relative z-10">
                <span className="text-[10px] uppercase tracking-[0.3em] text-gold-glow/80 mb-2 block font-bold">
                  {c.area}
                </span>
                <h2 className="text-2xl font-bold mb-3 text-white">
                  {c.title}
                </h2>
                <p className="legal-body text-sm text-ivory/50 mb-6 leading-relaxed">
                  {c.desc}
                </p>
                
                <div className="flex items-center justify-between mt-auto pt-6 border-t border-white/5">
                  <div className="flex flex-col">
                    <span className="text-[9px] uppercase tracking-wider text-ivory/30">Assigned Role</span>
                    <span className="text-sm font-semibold text-ivory/80 italic">{c.role}</span>
                  </div>
                  <div className="flex items-center text-gold-glow font-bold text-sm tracking-widest">
                    ARGUE <ChevronRight size={16} className="ml-1" />
                  </div>
                </div>
              </div>

              {/* Hover Glow Effect */}
              {hoveredCase === c.id && (
                <motion.div 
                  layoutId="glow"
                  className="absolute inset-0 bg-gold-glow/5 pointer-events-none"
                />
              )}
            </motion.div>
          ))}
        </div>

        {/* Bottom Metadata */}
        <div className="mt-20 flex gap-12 text-[10px] uppercase tracking-[0.4em] text-ivory/20 font-bold">
          <div className="flex items-center gap-2"><Gavel size={12} /> Legal soundness</div>
          <div className="flex items-center gap-2"><Shield size={12} /> Strategy</div>
          <div className="flex items-center gap-2"><BookOpen size={12} /> Historical Accuracy</div>
        </div>
      </motion.div>

      {/* Tech Overlay Accents */}
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none overflow-hidden opacity-20">
        <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-gold-glow/5 blur-[120px]" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-walnut-warm/20 blur-[120px]" />
      </div>
    </div>
  );
}

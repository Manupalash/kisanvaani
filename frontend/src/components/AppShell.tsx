"use client";

import { ReactNode, useState } from "react";
import { Menu, Bell, Sprout } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [telugu, setTelugu] = useState(true);
  return <div className="app-shell"><Sidebar open={menuOpen} onClose={() => setMenuOpen(false)}/><main className="main"><header className="topbar"><button className="icon-btn mobile-menu" aria-label="Open menu" onClick={() => setMenuOpen(true)}><Menu size={18}/></button><div className="mobile-brand"><div className="brand-mark"><Sprout size={17}/></div>KisanVaani</div><div className="crumb">Your farm companion <span className="mx-2 text-stone-300">/</span> <span className="text-forest">నమస్కారం</span></div><div className="top-actions"><select className="language" aria-label="Select language" value={telugu ? "te" : "en"} onChange={(e) => setTelugu(e.target.value === "te")}><option value="te">తెలుగు</option><option value="en">English</option></select><button className="icon-btn" aria-label="Notifications"><Bell size={16}/><i className="dot"/></button></div></header>{children}</main></div>;
}

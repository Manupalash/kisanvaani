"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sprout, LayoutDashboard, Mic2, Clock3, UserRound, Wheat, Leaf, X } from "lucide-react";

const links = [
  { href: "/", label: "Home", icon: LayoutDashboard },
  { href: "/assistant", label: "Voice assistant", icon: Mic2 },
  { href: "/history", label: "Conversations", icon: Clock3 },
  { href: "/crops", label: "My crops", icon: Wheat },
  { href: "/advisory", label: "Advisory", icon: Leaf },
  { href: "/profile", label: "Farmer profile", icon: UserRound },
];

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const path = usePathname();
  return <>
    {open && <button aria-label="Close menu" className="fixed inset-0 z-10 bg-black/30 md:hidden" onClick={onClose} />}
    <aside className={`sidebar ${open ? "open" : ""}`}>
      <div className="brand"><div className="brand-mark"><Sprout size={22} /></div><div><div className="brand-name">KisanVaani</div><div className="brand-sub">Your farm companion</div></div><button className="ml-auto md:hidden" onClick={onClose} aria-label="Close"><X size={19}/></button></div>
      <div className="nav-label">Workspace</div>
      <nav className="nav-list">{links.map(({ href, label, icon: Icon }) => <Link key={href} href={href} onClick={onClose} className={`nav-item ${path === href ? "active" : ""}`}><Icon size={17}/><span>{label}</span></Link>)}</nav>
      <div className="sidebar-bottom"><div className="season-card"><p>YOUR FARM · TELANGANA</p><strong>🌱 Kharif season</strong><span>Season progress · 68%</span></div><div className="profile-mini"><div className="avatar">రా</div><div><strong>రాములు నాయక్</strong><span>Farmer · Nalgonda</span></div></div></div>
    </aside>
  </>;
}

"use client"

import { Check, ChevronRight, Shield, Zap, TrendingUp, Globe, Lock, Star } from "lucide-react"

const premiumFeatures = [
  { icon: Zap, text: "Unlimited AI Coach chats" },
  { icon: TrendingUp, text: "Full Polymarket divergence feed" },
  { icon: Globe, text: "All 48 group stage match picks" },
  { icon: Shield, text: "Knockout bracket predictions" },
  { icon: Star, text: "Live odds movement alerts" },
]

const menuItems = [
  { label: "Notification Settings", icon: ChevronRight },
  { label: "Responsible Gambling", icon: ChevronRight },
  { label: "Help & Support", icon: ChevronRight },
  { label: "Privacy Policy", icon: ChevronRight },
]

export default function Profile() {
  return (
    <div className="flex flex-col h-full overflow-y-auto pb-6">
      {/* Header */}
      <div className="px-5 pt-6 pb-5 flex-shrink-0">
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Profile</h1>
      </div>

      {/* User card */}
      <div className="mx-5 mb-5 rounded-2xl bg-[#0F1C35] border border-[#1A2845] p-4 flex items-center gap-4">
        <div className="relative">
          <div className="w-14 h-14 rounded-full bg-gradient-to-br from-[#00FF87]/30 to-[#0F1C35] border-2 border-[#00FF87]/40 flex items-center justify-center flex-shrink-0">
            <span className="text-2xl">👤</span>
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-base font-bold text-foreground">Alex Rivera</p>
          <p className="text-xs text-[#6A7A9B]">alex@example.com</p>
          <div className="flex items-center gap-1.5 mt-1.5">
            <div className="bg-[#1A2845] rounded-full px-2.5 py-0.5">
              <span className="text-[10px] font-semibold text-[#6A7A9B] uppercase tracking-wider">Free Plan</span>
            </div>
          </div>
        </div>
        <button className="text-[#6A7A9B] hover:text-foreground transition-colors" aria-label="Edit profile">
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Usage */}
      <div className="mx-5 mb-5 rounded-2xl bg-card border border-[#1A2845] p-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-semibold text-foreground">Daily AI Chats</p>
          <span className="text-xs text-[#6A7A9B]">Resets midnight UTC</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex-1 h-2 rounded-full bg-[#1A2845] overflow-hidden">
            <div
              className="h-full rounded-full bg-[#00FF87] transition-all"
              style={{ width: "60%" }}
            />
          </div>
          <span className="text-sm font-bold text-foreground flex-shrink-0">3/5</span>
        </div>
        <p className="text-[11px] text-[#6A7A9B] mt-2">2 chats remaining today</p>
      </div>

      {/* Upgrade card */}
      <div className="mx-5 mb-5 rounded-2xl overflow-hidden border border-[#00FF87]/30 relative">
        {/* Glow effect */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#00FF87]/5 to-transparent pointer-events-none" />

        <div className="relative p-5">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-[#00FF87]" />
              <span className="text-[10px] font-bold tracking-widest uppercase text-[#00FF87]">World Cup Pass</span>
            </div>
            <div className="flex items-baseline gap-0.5">
              <span className="text-2xl font-black text-foreground">€9.99</span>
              <span className="text-xs text-[#6A7A9B]">one time</span>
            </div>
          </div>
          <p className="text-lg font-bold text-foreground mb-4">
            Unlock Every Pick for the Full Tournament
          </p>

          <ul className="flex flex-col gap-2.5 mb-5">
            {premiumFeatures.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3">
                <div className="w-5 h-5 rounded-full bg-[#00FF87]/15 border border-[#00FF87]/30 flex items-center justify-center flex-shrink-0">
                  <Check className="w-3 h-3 text-[#00FF87]" />
                </div>
                <span className="text-sm text-[#A8B4D0]">{text}</span>
              </li>
            ))}
          </ul>

          <button className="w-full bg-[#00FF87] text-[#070D1A] font-bold text-sm py-3.5 rounded-xl hover:bg-[#00e87a] active:scale-[0.98] transition-all shadow-[0_0_20px_rgba(0,255,135,0.3)]">
            Upgrade Now · €9.99
          </button>
          <p className="text-center text-[10px] text-[#6A7A9B] mt-2.5">
            Powered by Stripe · Secure checkout · No subscription
          </p>
        </div>
      </div>

      {/* Menu items */}
      <div className="mx-5 rounded-2xl bg-card border border-[#1A2845] overflow-hidden">
        {menuItems.map(({ label, icon: Icon }, index) => (
          <button
            key={label}
            className={`w-full flex items-center justify-between px-4 py-3.5 text-sm text-[#A8B4D0] hover:bg-[#0F1C35] active:bg-[#0F1C35] transition-colors ${
              index < menuItems.length - 1 ? "border-b border-[#1A2845]" : ""
            }`}
          >
            <span>{label}</span>
            <Icon className="w-4 h-4 text-[#6A7A9B]" />
          </button>
        ))}
      </div>
    </div>
  )
}

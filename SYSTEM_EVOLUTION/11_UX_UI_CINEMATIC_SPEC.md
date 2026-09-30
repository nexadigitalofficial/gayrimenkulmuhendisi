# 🎬 SPECIFICATION: CINEMATIC DESIGN SYSTEM & SPATIAL UX
**Document Code:** SYS-EVO-11-UX-SPEC  
**Scope:** Phase 2 Implementation (P-003)

### 1. Design Tokens & Variables
`css
:root {
  --bg-deep-obsidian: #030712;
  --bg-cyber-navy: #0a1128;
  --gold-imperial-500: #d4af37;
  --gold-imperial-gradient: linear-gradient(135deg, #f59e0b 0%, #d4af37 50%, #b45309 100%);
  --emerald-jade-gradient: linear-gradient(135deg, #10b981 0%, #059669 100%);
  --glass-border: rgba(212, 175, 55, 0.2);
  --glass-surface: rgba(15, 23, 42, 0.75);
}
`

### 2. Micro-Interactions & Hardware Acceleration
- **Card Hover Physics:** will-change: transform; transform: translateY(-4px) scale(1.01);
- **Instant Persona Shimmer:** Sleek gold-line wireframe animation while persona data loads.
- **Adaptive Badging:** Satılık items pulse with Royal Gold glow; Kiralık items pulse with Emerald Jade glow.

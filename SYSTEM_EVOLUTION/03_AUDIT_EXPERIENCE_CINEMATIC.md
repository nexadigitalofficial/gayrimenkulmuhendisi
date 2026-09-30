# 🎨 AUDIT: PRODUCT EXPERIENCE & CINEMATIC DESIGN
**Document Code:** SYS-EVO-03-CINEMATIC  
**Authors:** UI/UX & Cinematic Design Studio + Product & Experience Company  
**Target:** Client Facing Portals (site.html, ilanlar.html, projeler.html, sunum.html)

---

### 1. Aesthetic DNA & Visual Hierarchy
- **Palette Identity:**
  - Background: Deep Obsidian Navy (#030712, #0a1128)
  - Accent Prestige: Imperial Brushed Gold (#d4af37, #f59e0b, #eab308)
  - Semantic Status: Emerald Jade (#10b981 for Kiralık), Royal Gold (#d4af37 for Satılık), Slate Mist (#94a3b8 for Secondary text)
- **Typography:** Inter / Plus Jakarta Sans / Playfair Display headings.
- **Glassmorphism:** High-end backdrop blur (ackdrop-blur-xl bg-slate-900/80 border border-amber-500/20).

---

### 2. Cinematic & Motion Audit
1. **Current Motion Strengths:**
   - Smooth hero reveals, parallax scroll triggers, clean modal spring transitions.
   - Persona modal with dynamic theme shift based on Satılık (Gold) vs Kiralık (Emerald).
2. **Motion Bottlenecks:**
   - Multi-layer backdrop filters on mobile devices can cause frame drops on mid-range phones.
   - Heavy image assets lack responsive srcset and AVIF/WebP formats, causing visual pop-in.
3. **Micro-Interaction Opportunities:**
   - **Spatial Card Tilt:** Hardware-accelerated 3D card tilt on hover (	ransform: perspective(1000px) rotateX(...) rotateY(...)).
   - **Instant Persona Shimmer:** While persona AI models compute, display a sleek gold-wireframe skeleton loader rather than a generic spinner.
   - **Interactive ROI Calculator Slider:** Haptic-feeling numeric count-up animations for rental yield and capital appreciation.

---

### 3. Proposed Cinematic Evolution
- **Componentized Card System:** Standardize listing cards into reusable macro-components with unified micro-animations.
- **Interactive Floorplan Explorer:** Deep-zoom vector viewer for luxury penthouse and villa layouts.
- **Ultra-Fast Persona Peek:** Hover-activated mini-persona summary before opening the full cinematic modal.

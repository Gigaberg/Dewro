# Wintage - Premium Landing Page Specification

**Role:** You are an award-winning UI/UX designer and elite frontend web developer. Your task is to perfectly recreate the "Wintage" landing page according to the highly detailed specification provided below. You must pay obsessive attention to every typographic detail, micro-interaction, and layout structure to achieve a world-class, premium Apple-inspired aesthetic.

## 1. Technical Architecture & Setup
- **Core Stack:** Pure HTML5 and Tailwind CSS (via CDN). Do not use React, Vue, or any build tools.
- **Tailwind Configuration:** Embed a `<script>` tag in the `<head>` configuring the Tailwind theme extensions.
- **Dependencies:** Google Fonts (Inter and Playfair Display).
- **File Structure:** A single `index.html` file containing all markup, custom CSS (in a `<style>` block), and vanilla JavaScript.

## 2. Visual Design System

### 2.1 Color Palette
- **Primary Text (Dark):** `text-slate-900` (#0f172a)
- **Secondary Text (Dark):** `text-slate-700` (#334155)
- **Accent/Brand:** Yellow star icon (`text-yellow-300/90`)
- **Background Tints:**
  - Video overlay: `bg-blue-900/5` (extremely subtle contrast adjustment)
  - Glass Navbar: Linear gradient from `rgba(0,0,0,0.3)` to `rgba(0,0,0,0)`
  - Radial Glass Container: Radial gradient from `rgba(255,255,255,0.4)` to transparent.
  - Mobile Menu Overlay: `bg-slate-900/95`

### 2.2 Typography
- **Primary Font (Sans-serif):** 'Inter', sans-serif (Weights: 300, 400, 500, 600, 700, 800, 900)
- **Secondary Font (Serif):** 'Playfair Display', serif (Weights: 500, 600, 700, 800, 900)
- **Hero Headline:** 
  - Font: Inter (Sans-serif)
  - Weight: Black (900)
  - Sizes: `text-5xl` (mobile), `text-6xl` (tablet), `text-[5.5rem]` (desktop)
  - Tracking: `tracking-tighter`
  - Leading: `leading-none`
- **Hero Description:**
  - Font: Inter
  - Weight: Semibold (600)
  - Sizes: `text-xl` (mobile), `text-2xl` (tablet)

### 2.3 Custom CSS & Visual Effects
- **Text Stroke (Shadow Trick):** 
  To prevent inward-overlapping strokes on heavy fonts, use a multi-directional `text-shadow` trick to create a crisp outer stroke.
  - Headline stroke: 8-point heavy shadow using `rgba(255,255,255,0.95)` at 2px offsets.
  - Description stroke: 8-point thin shadow using `rgba(255,255,255,0.9)` at 1px offsets.
- **Radial Blur Glass Container (`.radial-blur-container`):**
  - A highly advanced glassmorphism orb effect without sharp edges.
  - Base: `backdrop-filter: blur(24px)`
  - Background: `radial-gradient(ellipse at center, rgba(255, 255, 255, 0.4) 0%, rgba(255, 255, 255, 0) 70%)`
  - CSS Mask: `-webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 70%)` to smoothly fade the blur out at the edges.

## 3. Media Assets
- **Background Video:** 
  - URL: `https://strvid.nyc3.cdn.digitaloceanspaces.com/motionsite/animated_winter_village.mp4`
  - Attributes: `autoplay`, `muted`, `loop`, `playsinline`, `object-cover`
  - Positioning: Fixed behind all content (`z-0`), occupying the full screen `inset-0`.

## 4. UI Components & Section Hierarchy

### 4.1 Global Wrapper
- The body should have `overflow-x-hidden` and `text-slate-900`.
- Main content area should be wrapped in a `<main>` tag with `min-h-[90dvh] flex flex-col justify-end items-center max-w-7xl mx-auto px-6 z-10`.

### 4.2 Navigation Bar (`nav`)
- **Positioning:** Fixed at the top, full width, `z-50`, height 24 (`h-24`).
- **Background:** Custom `.glass-nav` class (dark linear gradient fading down).
- **Logo Area:** Text "Wintage" (`text-2xl font-bold text-white tracking-tight`) accompanied by a 4-point SVG star icon colored `text-yellow-300/90`.
- **Desktop Links:** "Home", "Categories" (with a dropdown arrow SVG), "Trending", "About us", "Contact". Styled as `text-sm font-medium text-white/95 hover:text-white`. Hidden on mobile.
- **Desktop Actions:** "Sign in" link and a "Get started" button (Solid white, slate text, fully rounded, `active:scale-95`).
- **Mobile Toggle:** Hamburger menu icon (`md:hidden`) that toggles to a close (X) icon when the menu is active.

### 4.3 Mobile Menu Overlay
- **Positioning:** `fixed inset-0 z-40`.
- **Styling:** Dark frosted glass (`bg-slate-900/95 backdrop-blur-2xl`).
- **Animation:** Slides in from the right (`translate-x-full` transition over 300ms).
- **Content:** Large typography (`text-2xl text-white/90`) stacking the nav links, separated by a faint horizontal rule, followed by the "Sign in" and full-width "Get started" button.

### 4.4 Hero Content Section
- **Positioning:** Anchored towards the bottom center of the screen (`justify-end items-center`).
- **Wrapper:** `max-w-6xl w-full text-center mb-4`.
- **Glass Container:** Uses the custom `.radial-blur-container` with huge padding (`p-12 md:p-24`) and an entrance animation.
- **Headline:** "Discover Wintage<br>Things, Everywhere"
- **Description:** "Explore handpicked places, services, and experiences<br class='hidden md:block'> that make life better."

## 5. Animations & Micro-Interactions

### 5.1 Tailwind Config Keyframes
Define these custom keyframes and animations in the Tailwind config block:
- `fadeInUp`: Translates Y from 30px to 0px, opacity 0 to 1. Duration: 1s, Ease: `cubic-bezier(0.16, 1, 0.3, 1)`.
- `slideDown`: Translates Y from -100% to 0px, opacity 0 to 1. Duration: 0.8s, Ease: `cubic-bezier(0.16, 1, 0.3, 1)`.

### 5.2 Element Animations
- **Navbar:** Enters with `animate-slide-down`.
- **Hero Container:** Enters with `animate-fade-in-up` (opacity-0 initial state).
- **Hover States:** Nav links transition to solid white (`transition-colors`). The "Get started" button scales down slightly on click (`active:scale-95`).

## 6. Vanilla JavaScript Implementation
- Implement a script at the end of the `<body>` to handle the mobile menu toggle.
- Grab the button, menu, and both SVG icons (hamburger and close).
- On click, toggle the `translate-x-full` class on the menu overlay.
- Swap the visibility classes (`block` vs `hidden`) of the hamburger and close icons based on the menu state.
- Lock body scrolling (`document.body.style.overflow = 'hidden'`) when the menu is open, and restore it (`'auto'`) when closed to prevent scrolling the page beneath the overlay.

## 7. Responsive Behavior
- **Mobile First:** All base classes must be tailored for mobile (e.g., small fonts, hamburger menu).
- **Tablet (`md:`):** Reveals desktop navigation, hides hamburger button, increases hero padding, switches `<br>` visibility in paragraphs.
- **Desktop (`lg:`):** Scales hero typography up to `text-[5.5rem]`.
- Assure proper spacing, grid structures, and legibility across all viewport sizes.

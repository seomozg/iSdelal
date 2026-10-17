# click-ai-widget — React SPA

Landing page and admin dashboard for **iSdelal** (the RAG backend lives in
`../backend`).

## What's inside

- **Landing page** (`src/pages/Index.tsx`) — marketing page with the demo widget,
  a Telegram-bot banner, pricing and FAQ.
- **Admin dashboard** (`src/pages/dashboard/`) — sites management, per-site
  usage stats, widget code generator, tariffs and billing, profile.
- **Auth** (`src/contexts/AuthContext.tsx`) — Google Sign-In + JWT.
- **i18n** (`src/contexts/LanguageContext.tsx`) — RU / EN.
- **UI kit** (`src/components/ui/`) — generated [shadcn/ui](https://ui.shadcn.com) components.

## Stack

Vite · React 18 · TypeScript · Tailwind CSS · shadcn/ui · framer-motion · react-router.

## Commands

```bash
npm install
npm run dev        # dev server (http://localhost:8080), proxies /api, /widget, /chat to :8000
npm run build      # production build → dist/
npm run lint       # eslint
```

## Structure

```
src/
  components/      UI components (Hero, Pricing, TgBanner, DashboardLayout, ui/*)
  contexts/        AuthContext, LanguageContext
  hooks/           use-toast, use-mobile
  lib/             api client, telegram deep-link helpers, utils
  pages/           Index (landing), Login, dashboard/*
  main.tsx         entry point
  App.tsx          routes
```

The production bundle is committed to `dist/` and served by nginx as the site
root; the admin dashboard lives under `/dashboard/*` (SPA fallback).

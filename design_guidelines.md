{
  "brand": {
    "name": "KONNTO AI",
    "design_personality": [
      "AI-native, premium, futuristic",
      "trustworthy for money + approvals",
      "India-first SMB friendly (high readability, big touch targets)",
      "calm on data screens, bold on AI touchpoints"
    ],
    "logo": {
      "source_url": "https://customer-assets-lqy194kg.emergentagent.net/job_konnto-plan--87psd4r7/artifacts/fa88f4351d22efae_KONNTO%20Logo%20on%20Blue%20Gradient.png",
      "notes": "Use as brand anchor. Recreate mark as inline SVG component (JS) so it stays crisp in both themes. Keep wordmark Montserrat-like: wide, geometric, bold."
    },
    "inspiration_refs": {
      "visual_refs": [
        {
          "title": "Modeinspect AI chat interface gallery",
          "url": "https://modeinspect.com/gallery/ai-chat-interface",
          "takeaways": [
            "floating glass composer",
            "AI speaker seam/glow",
            "orb/voice blob as presence"
          ]
        },
        {
          "title": "Glassmorphic AI Chat Interface (Dribbble)",
          "url": "https://dribbble.com/shots/26311046-Glassmorphic-AI-Chat-Interface-Skincare-Assistant",
          "takeaways": [
            "frosted panels + subtle borders",
            "premium spacing + soft shadows"
          ]
        },
        {
          "title": "60fps.design voice blob interactions",
          "url": "https://60fps.design/shots/chatgpt-voice-blob-gradient-interaction",
          "takeaways": [
            "orb states: idle/thinking/streaming",
            "motion that feels alive but not chaotic"
          ]
        }
      ],
      "implementation_refs": [
        {
          "title": "Liquid glass / shimmer border patterns",
          "url": "https://www.uistyleguide.com/style/liquid-glass",
          "takeaways": [
            "mask-composite border isolation",
            "conic-gradient shimmer"
          ]
        }
      ]
    }
  },

  "typography": {
    "google_fonts_import": "@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;800&family=Figtree:wght@400;500;600&family=Roboto+Mono:wght@400;500;600&display=swap');",
    "font_families": {
      "display": "Montserrat, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif",
      "body": "Figtree, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif",
      "mono": "Roboto Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace"
    },
    "type_scale_tailwind": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl font-display font-extrabold tracking-tight",
      "h2": "text-base md:text-lg text-muted-foreground",
      "h3": "text-xl sm:text-2xl font-display font-bold",
      "body": "text-sm sm:text-base leading-relaxed",
      "small": "text-xs sm:text-sm text-muted-foreground",
      "kpi_number": "font-mono tabular-nums text-2xl sm:text-3xl"
    },
    "copy_tone": {
      "rules": [
        "Short, directive sentences.",
        "Use business language: 'Approve', 'Delegate', 'Due today', 'Overdue'.",
        "Avoid slang; keep friendly but crisp.",
        "Use ₹ formatting consistently."
      ]
    }
  },

  "color_system": {
    "notes": [
      "Theme via CSS variables (HSL) using shadcn conventions.",
      "Dark is default: deep midnight blue with soft blue glows (logo-like).",
      "Light: clean white with royal blue highlights + red accents.",
      "No purple/pink gradients. Gradients only for hero/CTA/orb/decor (<20% viewport)."
    ],

    "tokens_css": {
      "paste_into": "/app/frontend/src/index.css (replace existing :root tokens; add .dark)",
      "css": "@layer base {\n  :root {\n    /* Fonts */\n    --font-sans: 'Figtree', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;\n    --font-display: 'Montserrat', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;\n    --font-mono: 'Roboto Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;\n\n    /* Light theme — clean white + royal blue + red accents */\n    --background: 210 33% 99%;\n    --foreground: 222 35% 12%;\n\n    --card: 0 0% 100%;\n    --card-foreground: 222 35% 12%;\n\n    --popover: 0 0% 100%;\n    --popover-foreground: 222 35% 12%;\n\n    --primary: 224 100% 58%; /* royal blue */\n    --primary-foreground: 0 0% 100%;\n\n    --secondary: 220 22% 96%;\n    --secondary-foreground: 222 35% 12%;\n\n    --muted: 220 22% 96%;\n    --muted-foreground: 218 16% 42%;\n\n    --accent: 224 100% 96%;\n    --accent-foreground: 224 100% 32%;\n\n    --destructive: 356 92% 56%;\n    --destructive-foreground: 0 0% 100%;\n\n    --border: 220 18% 88%;\n    --input: 220 18% 88%;\n    --ring: 224 100% 58%;\n\n    --radius: 1rem;\n\n    /* Brand extras */\n    --brand-blue-1: 224 100% 58%; /* #0047FF-ish */\n    --brand-blue-2: 221 100% 46%; /* deeper */\n    --brand-navy-1: 224 78% 18%;\n    --brand-navy-2: 226 86% 12%;\n    --brand-red: 356 100% 58%;\n\n    /* Glass surfaces (light) */\n    --glass-bg: 0 0% 100% / 0.72;\n    --glass-border: 224 40% 40% / 0.14;\n    --glass-shadow: 224 40% 20% / 0.10;\n\n    /* Glow */\n    --glow-blue: 224 100% 60% / 0.22;\n    --glow-cyan: 198 100% 55% / 0.14;\n\n    /* Status */\n    --status-overdue: 8 86% 52%;\n    --status-due: 38 92% 50%;\n    --status-stuck: 220 10% 46%;\n    --status-done: 152 55% 38%;\n    --status-open: 224 100% 58%;\n    --status-pending: 38 92% 50%;\n    --status-decided: 152 55% 38%;\n\n    /* Charts */\n    --chart-1: 224 100% 58%;\n    --chart-2: 198 100% 45%;\n    --chart-3: 38 92% 50%;\n    --chart-4: 8 86% 52%;\n    --chart-5: 152 55% 38%;\n\n    /* Motion */\n    --ease: cubic-bezier(0.2, 0.8, 0.2, 1);\n  }\n\n  .dark {\n    /* Dark theme — deep midnight blue + soft blue glows */\n    --background: 226 86% 8%;\n    --foreground: 210 40% 96%;\n\n    --card: 226 70% 10%;\n    --card-foreground: 210 40% 96%;\n\n    --popover: 226 70% 10%;\n    --popover-foreground: 210 40% 96%;\n\n    --primary: 224 100% 62%;\n    --primary-foreground: 0 0% 100%;\n\n    --secondary: 226 40% 14%;\n    --secondary-foreground: 210 40% 96%;\n\n    --muted: 226 40% 14%;\n    --muted-foreground: 218 18% 70%;\n\n    --accent: 224 60% 18%;\n    --accent-foreground: 210 40% 96%;\n\n    --destructive: 356 92% 60%;\n    --destructive-foreground: 0 0% 100%;\n\n    --border: 224 30% 22%;\n    --input: 224 30% 22%;\n    --ring: 224 100% 62%;\n\n    /* Brand extras */\n    --brand-blue-1: 224 100% 62%;\n    --brand-blue-2: 221 100% 50%;\n    --brand-navy-1: 226 86% 12%;\n    --brand-navy-2: 226 86% 8%;\n    --brand-red: 356 100% 60%;\n\n    /* Glass surfaces (dark) */\n    --glass-bg: 226 70% 10% / 0.62;\n    --glass-border: 210 40% 98% / 0.10;\n    --glass-shadow: 224 80% 30% / 0.18;\n\n    /* Glow */\n    --glow-blue: 224 100% 62% / 0.28;\n    --glow-cyan: 198 100% 55% / 0.18;\n\n    /* Status */\n    --status-overdue: 8 86% 58%;\n    --status-due: 38 92% 56%;\n    --status-stuck: 220 10% 62%;\n    --status-done: 152 55% 46%;\n    --status-open: 224 100% 62%;\n    --status-pending: 38 92% 56%;\n    --status-decided: 152 55% 46%;\n\n    /* Charts */\n    --chart-1: 224 100% 62%;\n    --chart-2: 198 100% 55%;\n    --chart-3: 38 92% 56%;\n    --chart-4: 8 86% 58%;\n    --chart-5: 152 55% 46%;\n  }\n}\n\n@layer base {\n  html, body {\n    font-family: var(--font-sans);\n    -webkit-font-smoothing: antialiased;\n    -moz-osx-font-smoothing: grayscale;\n  }\n  h1, h2, h3, h4, .font-display {\n    font-family: var(--font-display);\n    letter-spacing: -0.015em;\n  }\n  code, pre, .font-mono {\n    font-family: var(--font-mono);\n  }\n  ::selection {\n    background: hsl(var(--brand-blue-1) / 0.22);\n    color: hsl(var(--foreground));\n  }\n}\n"
    },

    "gradient_recipes": {
      "allowed_usage": [
        "Landing hero background only (<=20% viewport)",
        "Primary CTA button background",
        "KONNTO Orb layers",
        "Small decorative accents (e.g., 1-2 corner glows)"
      ],
      "hero_bg_dark": "radial-gradient(900px circle at 20% 0%, hsl(224 100% 62% / 0.22), transparent 55%), radial-gradient(700px circle at 85% 10%, hsl(198 100% 55% / 0.14), transparent 52%), radial-gradient(900px circle at 50% 120%, hsl(356 100% 60% / 0.10), transparent 55%)",
      "hero_bg_light": "radial-gradient(900px circle at 20% 0%, hsl(224 100% 58% / 0.14), transparent 55%), radial-gradient(700px circle at 85% 10%, hsl(198 100% 45% / 0.10), transparent 52%)",
      "primary_button": "linear-gradient(135deg, hsl(224 100% 62%), hsl(221 100% 50%))"
    }
  },

  "layout": {
    "grid_and_spacing": {
      "app_shell": {
        "desktop": "Left rail 280px (sticky), content max-w-[1200px] with 24px gutters; topbar 56px glass.",
        "mobile": "Bottom tab bar height 68px + safe-area; content padding 16px; composer floats above tab bar."
      },
      "spacing_rules": [
        "Use 2–3x more whitespace than typical SaaS.",
        "Cards: p-4 (mobile) / p-5 (desktop).",
        "Section spacing: py-10 (mobile) / py-16 (desktop).",
        "List rows: min-h 56px; touch targets >=44px."
      ]
    },
    "z_index_scale": {
      "z_base": 0,
      "z_header": 40,
      "z_bottom_tabs": 45,
      "z_sheet": 50,
      "z_dialog": 60,
      "z_toast": 70,
      "z_tooltip": 80
    }
  },

  "texture_and_glass": {
    "noise_overlay": {
      "class": ".noise",
      "opacity": "0.03–0.05 (3–5%)",
      "notes": "Apply to large surfaces only (page backgrounds, hero). Avoid on dense text blocks."
    },
    "glass_recipe": {
      "tailwind": "bg-[hsl(var(--glass-bg))] border border-[hsl(var(--glass-border))] shadow-[0_12px_40px_hsl(var(--glass-shadow))] backdrop-blur-[18px] backdrop-saturate-[140%]",
      "fallback": "@supports not (backdrop-filter: blur(1px)) { use solid card background }",
      "where": [
        "Topbar",
        "Bottom tab bar",
        "Composer",
        "Sheets/Dialogs/Dropdowns",
        "Proposal cards (AI)"
      ]
    }
  },

  "motion": {
    "principles": [
      "No transition: all. Only transition colors/opacity/box-shadow/transform.",
      "UI interactions: 150–250ms.",
      "Looping animations only for orb/shimmer; keep subtle.",
      "Respect prefers-reduced-motion: reduce loops to static gradients."
    ],
    "keyframes_css": {
      "paste_into": "/app/frontend/src/index.css (below utilities)",
      "css": "@property --shimmer-angle {\n  syntax: '<angle>';\n  inherits: true;\n  initial-value: 0deg;\n}\n\n@keyframes konnto-orb-float {\n  0%, 100% { transform: translateY(0); }\n  50% { transform: translateY(-6px); }\n}\n\n@keyframes konnto-orb-breathe {\n  0%, 100% { transform: scale(1); filter: drop-shadow(0 0 0 hsl(var(--glow-blue))); }\n  50% { transform: scale(1.02); filter: drop-shadow(0 0 18px hsl(var(--glow-blue))); }\n}\n\n@keyframes konnto-orb-spin {\n  to { --shimmer-angle: 360deg; }\n}\n\n@keyframes konnto-typing {\n  0%, 80%, 100% { opacity: 0.25; transform: translateY(0); }\n  40% { opacity: 1; transform: translateY(-3px); }\n}\n\n@keyframes konnto-trail {\n  0% { opacity: 0; transform: translateX(-8px); }\n  30% { opacity: 1; }\n  100% { opacity: 0; transform: translateX(10px); }\n}\n\n@media (prefers-reduced-motion: reduce) {\n  .orb-animate, .shimmer-animate, .trail-animate { animation: none !important; }\n}\n"
    },
    "micro_interactions": {
      "buttons": "hover: translateY(-1px) + glow; active: scale(0.98)",
      "cards": "hover: border brightens + subtle lift",
      "tabs": "active pill slides (transform only)",
      "chat_streaming": "assistant bubble gets a faint animated shimmer seam"
    }
  },

  "ai_orb": {
    "definition": "KONNTO Orb is the AI presence: assistant avatar in chat, large in empty states/onboarding/landing hero.",
    "states": [
      {
        "name": "idle",
        "behavior": "slow breathe + float",
        "duration": "6s breathe, 8s float"
      },
      {
        "name": "thinking",
        "behavior": "slightly faster breathe + subtle inner swirl",
        "duration": "3.6s"
      },
      {
        "name": "streaming",
        "behavior": "conic shimmer rotates + outer ring pulses",
        "duration": "1.6s"
      }
    ],
    "css_recipe": {
      "notes": "Use a div with pseudo-elements for layers. Keep size responsive via CSS vars.",
      "css": ".konnto-orb {\n  --orb-size: 56px;\n  width: var(--orb-size);\n  height: var(--orb-size);\n  border-radius: 999px;\n  position: relative;\n  isolation: isolate;\n  background: radial-gradient(circle at 30% 25%, hsl(var(--brand-blue-1) / 0.95), transparent 55%),\n              radial-gradient(circle at 70% 75%, hsl(198 100% 55% / 0.55), transparent 60%),\n              radial-gradient(circle at 50% 50%, hsl(var(--brand-navy-1) / 1), hsl(var(--brand-navy-2) / 1));\n  box-shadow: 0 0 0 1px hsl(var(--glass-border)),\n              0 18px 60px hsl(var(--glow-blue)),\n              0 10px 30px hsl(var(--glow-cyan));\n}\n\n.konnto-orb::before {\n  content: '';\n  position: absolute;\n  inset: -1px;\n  border-radius: inherit;\n  background: conic-gradient(from var(--shimmer-angle),\n    transparent 0deg,\n    hsl(var(--brand-blue-1) / 0.55) 60deg,\n    transparent 120deg,\n    hsl(198 100% 55% / 0.35) 200deg,\n    transparent 260deg,\n    hsl(var(--brand-red) / 0.22) 320deg,\n    transparent 360deg\n  );\n  filter: blur(10px);\n  opacity: 0.55;\n  z-index: -1;\n}\n\n.konnto-orb::after {\n  content: '';\n  position: absolute;\n  inset: 10%;\n  border-radius: inherit;\n  background: radial-gradient(circle at 35% 30%, rgba(255,255,255,0.55), transparent 45%);\n  mix-blend-mode: overlay;\n  opacity: 0.55;\n}\n\n.konnto-orb.orb-animate {\n  animation: konnto-orb-breathe 6s var(--ease) infinite;\n}\n\n.konnto-orb.orb-float {\n  animation: konnto-orb-float 8s var(--ease) infinite;\n}\n\n.konnto-orb.orb-streaming::before {\n  animation: konnto-orb-spin 1.6s linear infinite;\n}\n",
      "tailwind_wrapper": "relative rounded-full",
      "sizes": {
        "chat_avatar": "--orb-size: 40px",
        "empty_state": "--orb-size: 96px",
        "landing_hero": "--orb-size: 160px"
      }
    }
  },

  "shimmer_border": {
    "use_cases": [
      "AI proposal cards",
      "Morning brief card",
      "Onboarding highlight panels"
    ],
    "css": ".shimmer-border {\n  position: relative;\n  border-radius: calc(var(--radius) + 6px);\n}\n\n.shimmer-border::before {\n  content: '';\n  position: absolute;\n  inset: 0;\n  border-radius: inherit;\n  padding: 1px;\n  background: conic-gradient(from var(--shimmer-angle),\n    hsl(var(--brand-blue-1) / 0.0),\n    hsl(var(--brand-blue-1) / 0.55),\n    hsl(198 100% 55% / 0.35),\n    hsl(var(--brand-red) / 0.22),\n    hsl(var(--brand-blue-1) / 0.0)\n  );\n  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);\n  -webkit-mask-composite: xor;\n  mask-composite: exclude;\n  opacity: 0.9;\n}\n\n.shimmer-animate::before {\n  animation: konnto-orb-spin 3.2s linear infinite;\n}\n\n@media (prefers-reduced-motion: reduce) {\n  .shimmer-animate::before { animation: none; }\n}\n",
    "notes": "Apply to a wrapper div; inner card stays readable (solid card bg)."
  },

  "components": {
    "component_path": {
      "button": "/app/frontend/src/components/ui/button.jsx",
      "card": "/app/frontend/src/components/ui/card.jsx",
      "tabs": "/app/frontend/src/components/ui/tabs.jsx",
      "badge": "/app/frontend/src/components/ui/badge.jsx",
      "sheet": "/app/frontend/src/components/ui/sheet.jsx",
      "dialog": "/app/frontend/src/components/ui/dialog.jsx",
      "dropdown": "/app/frontend/src/components/ui/dropdown-menu.jsx",
      "input": "/app/frontend/src/components/ui/input.jsx",
      "textarea": "/app/frontend/src/components/ui/textarea.jsx",
      "select": "/app/frontend/src/components/ui/select.jsx",
      "switch": "/app/frontend/src/components/ui/switch.jsx",
      "avatar": "/app/frontend/src/components/ui/avatar.jsx",
      "table": "/app/frontend/src/components/ui/table.jsx",
      "skeleton": "/app/frontend/src/components/ui/skeleton.jsx",
      "sonner_toast": "/app/frontend/src/components/ui/sonner.jsx",
      "calendar": "/app/frontend/src/components/ui/calendar.jsx"
    },

    "tailwind_recipes": {
      "buttons": {
        "primary": "bg-[linear-gradient(135deg,hsl(var(--brand-blue-1)),hsl(var(--brand-blue-2)))] text-primary-foreground shadow-[0_10px_30px_hsl(var(--glow-blue))] hover:shadow-[0_14px_40px_hsl(var(--glow-blue))] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))] focus-visible:ring-offset-2 focus-visible:ring-offset-background transition-[transform,box-shadow,filter] duration-200 ease-[var(--ease)] active:scale-[0.98]",
        "secondary_glass": "bg-[hsl(var(--glass-bg))] text-foreground border border-[hsl(var(--glass-border))] backdrop-blur-[18px] hover:border-[hsl(var(--brand-blue-1)/0.35)] transition-[transform,box-shadow,background-color,border-color] duration-200 ease-[var(--ease)] active:scale-[0.98]",
        "ghost": "bg-transparent hover:bg-accent hover:text-accent-foreground transition-[background-color,color] duration-150",
        "destructive": "bg-[hsl(var(--destructive))] text-[hsl(var(--destructive-foreground))] hover:brightness-[1.05] transition-[filter,transform] duration-200 active:scale-[0.98]"
      },
      "inputs": {
        "base": "bg-[hsl(var(--glass-bg))] border border-[hsl(var(--glass-border))] backdrop-blur-[14px] placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))] focus-visible:ring-offset-2 focus-visible:ring-offset-background transition-[border-color,box-shadow] duration-200",
        "textarea": "min-h-[96px] resize-none"
      },
      "tabs_pill_segmented": {
        "list": "inline-flex rounded-full bg-muted p-1",
        "trigger": "rounded-full px-3 py-1.5 text-sm data-[state=active]:bg-[hsl(var(--glass-bg))] data-[state=active]:shadow-[0_10px_30px_hsl(var(--glass-shadow))] transition-[background-color,box-shadow,color] duration-200"
      },
      "cards": {
        "base": "rounded-[calc(var(--radius)+6px)] bg-card text-card-foreground border border-border shadow-[0_10px_30px_hsl(var(--glass-shadow))]",
        "glass": "rounded-[calc(var(--radius)+6px)] bg-[hsl(var(--glass-bg))] border border-[hsl(var(--glass-border))] backdrop-blur-[18px] shadow-[0_12px_40px_hsl(var(--glass-shadow))]"
      },
      "badges_status": {
        "overdue": "bg-[hsl(var(--status-overdue)/0.14)] text-[hsl(var(--status-overdue))] border border-[hsl(var(--status-overdue)/0.22)]",
        "due": "bg-[hsl(var(--status-due)/0.16)] text-[hsl(var(--status-due))] border border-[hsl(var(--status-due)/0.24)]",
        "stuck": "bg-[hsl(var(--status-stuck)/0.14)] text-[hsl(var(--status-stuck))] border border-[hsl(var(--status-stuck)/0.22)]",
        "done": "bg-[hsl(var(--status-done)/0.14)] text-[hsl(var(--status-done))] border border-[hsl(var(--status-done)/0.22)]",
        "pending": "bg-[hsl(var(--status-pending)/0.16)] text-[hsl(var(--status-pending))] border border-[hsl(var(--status-pending)/0.24)]"
      },
      "kpi_tile": "rounded-2xl bg-[hsl(var(--glass-bg))] border border-[hsl(var(--glass-border))] backdrop-blur-[18px] p-4 shadow-[0_18px_60px_hsl(var(--glow-blue))]",
      "list_row": "flex items-center gap-3 rounded-xl px-3 py-3 hover:bg-accent transition-[background-color] duration-150",
      "skeleton": "bg-[linear-gradient(90deg,hsl(var(--muted)),hsl(var(--accent)),hsl(var(--muted)))] bg-[length:200%_100%] animate-[shimmer_1.2s_linear_infinite]"
    }
  },

  "chat_ui": {
    "bubbles": {
      "assistant": {
        "container": "max-w-[88%] rounded-2xl rounded-tl-md bg-[hsl(var(--glass-bg))] border border-[hsl(var(--glass-border))] backdrop-blur-[18px] px-4 py-3 shadow-[0_12px_40px_hsl(var(--glass-shadow))]",
        "seam": "before:content-[''] before:absolute before:left-0 before:top-3 before:bottom-3 before:w-[2px] before:rounded-full before:bg-[linear-gradient(180deg,hsl(var(--brand-blue-1)),hsl(198_100%_55%/0.0))]"
      },
      "user": {
        "container": "max-w-[88%] rounded-2xl rounded-tr-md bg-[linear-gradient(135deg,hsl(var(--brand-blue-1)),hsl(var(--brand-blue-2)))] text-white px-4 py-3 shadow-[0_18px_60px_hsl(var(--glow-blue))]"
      }
    },
    "composer": {
      "wrapper": "fixed bottom-[calc(68px+env(safe-area-inset-bottom)+12px)] left-0 right-0 px-3",
      "pill": "mx-auto max-w-[720px] rounded-full bg-[hsl(var(--glass-bg))] border border-[hsl(var(--glass-border))] backdrop-blur-[20px] shadow-[0_18px_60px_hsl(var(--glass-shadow))]",
      "input": "bg-transparent border-0 focus-visible:ring-0 focus-visible:ring-offset-0",
      "attachments_strip": "flex gap-2 overflow-x-auto no-scrollbar px-3 pb-2"
    },
    "voice_recording_bar": {
      "container": "rounded-2xl bg-[hsl(var(--glass-bg))] border border-[hsl(var(--glass-border))] backdrop-blur-[18px] p-3",
      "rec_dot": "w-2.5 h-2.5 rounded-full bg-[hsl(var(--brand-red))] animate-[pulse_1s_ease-in-out_infinite]"
    },
    "proposal_card": {
      "wrapper": "shimmer-border shimmer-animate",
      "inner": "rounded-[calc(var(--radius)+6px)] bg-card/80 dark:bg-[hsl(var(--card)/0.72)] backdrop-blur-[18px] p-4",
      "actions": "grid grid-cols-3 gap-2",
      "action_buttons": "Use shadcn Button variants; ensure exactly 3 actions: Save/Edit/Skip; then Saved+Undo"
    },
    "typing_dots": {
      "css": ".typing-dot{width:6px;height:6px;border-radius:999px;background:hsl(var(--brand-blue-1));display:inline-block;animation:konnto-typing 1.2s infinite ease-in-out}.typing-dot:nth-child(2){animation-delay:.15s}.typing-dot:nth-child(3){animation-delay:.3s}"
    }
  },

  "page_blueprints": {
    "landing": {
      "hero_concept": {
        "layout": "Z-pattern: left copy + CTA, right chat preview mock + orb. Mobile: stacked with orb above chat preview.",
        "bg": "Use hero_bg_dark in dark mode; hero_bg_light in light mode; keep gradient area <=20% viewport.",
        "sections": [
          "Hero: headline + subhead + CTA (Try in WhatsApp / Open app)",
          "How it works: 3 steps (Capture → Decide → Delegate)",
          "WhatsApp-first: phone mock + consent note",
          "Industries: retail/wholesale/construction/services cards",
          "Trust: approvals + audit trail + privacy",
          "Final CTA + footer"
        ]
      }
    },
    "today_dashboard": {
      "kpis": "4 KPI tiles in a 2x2 grid on mobile; 4x1 on desktop. Use mono numbers + status pills.",
      "brief_card": "Morning brief uses shimmer-border wrapper; includes 'Play' (voice) + 'Send to WhatsApp' actions.",
      "lists": "Overdue/Due lists as glass cards with list rows; show who’s waiting on whom as compact rows with avatars."
    },
    "work": {
      "filters": "Top segmented tabs (Open/Stuck/Done) + kind Select + Mine Switch + Search Input.",
      "detail": "Use Sheet (right side on desktop, bottom on mobile) with timeline + status buttons (Done/Delayed/Stuck)."
    },
    "team": {
      "rows": "Avatar + name + role + pills (App/WhatsApp). Use subtle hover highlight.",
      "invite_dialog": "Dialog with invite link Input + Copy button + QR optional.",
      "access_sheet": "Sheet with Checkbox list for permissions."
    },
    "approvals": {
      "cards": "Approval card with amount in mono, status pill, and 3 decision buttons: Allow once / Always under ₹X / Don’t allow.",
      "decided_tab": "Tabs with Decided; show Undo as ghost button."
    },
    "documents": {
      "upload": "Dropzone card (glass) with dashed border; show progress.",
      "detail_sheet": "Sheet with AI summary + found items list; highlight found items with subtle blue left border."
    },
    "business_brain": {
      "facts_rules": "Two-column on desktop, stacked on mobile. Each item is a compact card with edit actions."
    },
    "settings_privacy_help": {
      "pattern": "Form sections as cards; use Switch for toggles; destructive actions in AlertDialog with red accent."
    },
    "admin_console": {
      "tone": "More restrained: fewer glows, more solid surfaces; keep brand blue for focus + selection.",
      "tables": "Use shadcn Table with sticky header; row hover uses accent background."
    }
  },

  "clerk_appearance": {
    "notes": "Set Clerk appearance variables to match tokens for both themes (background, text, primary). Keep inputs glassy in dark, clean in light.",
    "suggested_vars": {
      "colorPrimary": "hsl(var(--primary))",
      "colorBackground": "hsl(var(--background))",
      "colorText": "hsl(var(--foreground))",
      "colorInputBackground": "hsl(var(--glass-bg))",
      "colorInputText": "hsl(var(--foreground))"
    }
  },

  "image_urls": {
    "landing_hero_orb_art": [
      {
        "url": "https://images.unsplash.com/photo-1653299832314-5d3dc1e5a83c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Nzh8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMGJsdWUlMjBncmFkaWVudCUyMG9yYiUyMDNkJTIwcmVuZGVyfGVufDB8fHxibHVlfDE3OTQ1OTExOTN8MA&ixlib=rb-4.1.0&q=85",
        "category": "landing",
        "description": "Abstract blue 3D orb render for hero side visual / background card"
      }
    ],
    "smb_owner": [
      {
        "url": "https://images.unsplash.com/photo-1792563739121-461a15147254?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxODh8MHwxfHNlYXJjaHwxfHxzbWFsbCUyMGJ1c2luZXNzJTIwb3duZXIlMjBpbmRpYSUyMHNob3AlMjBzbWFydHBob25lfGVufDB8fHx8MTc5NDU5MTE4N3ww&ixlib=rb-4.1.0&q=85",
        "category": "landing",
        "description": "India-first SMB vibe image for industries/trust section"
      }
    ],
    "team_collaboration": [
      {
        "url": "https://images.unsplash.com/flagged/photo-1576485436509-a7d286952b65?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDN8MHwxfHNlYXJjaHwxfHx0ZWFtJTIwY29sbGFib3JhdGlvbiUyMG9mZmljZSUyMGluZGlhJTIwc21hcnRwaG9uZXxlbnwwfHx8fDE3OTQ1OTExOTB8MA&ixlib=rb-4.1.0&q=85",
        "category": "landing",
        "description": "Team meeting image for Team/Delegation section"
      }
    ]
  },

  "accessibility": {
    "requirements": [
      "WCAG AA contrast in both themes.",
      "Focus-visible ring: 2px brand blue with offset.",
      "Touch targets >=44px.",
      "prefers-reduced-motion: disable orb/shimmer loops."
    ]
  },

  "instructions_to_main_agent": [
    "VISUAL REDESIGN ONLY: do not change functionality.",
    "Replace existing teal tokens in /app/frontend/src/index.css with the provided token set and add .dark tokens. Dark should be default (html has class 'dark' initially).",
    "Add Google Fonts import at top of index.css (Montserrat + Figtree + Roboto Mono).",
    "Implement theme toggle (Sun/Moon icons from lucide-react) in public nav, app topbar, admin topbar. Toggle by adding/removing 'dark' class on <html>.",
    "Create a reusable KONNTOLogo component as inline SVG (JS) and a KonntoOrb component (JS) using the CSS classes above.",
    "Apply glass recipe to overlays: Sheet/Dialog/Dropdown/Topbar/Bottom tabs/Composer.",
    "Implement shimmer-border utility class for AI proposal cards + brief card; ensure reduced-motion fallback.",
    "Chat: assistant bubble glass with seam; user bubble blue gradient; composer floating glass pill; typing dots use konnto-typing keyframes.",
    "Status pills: use Badge with status classes for overdue/due/stuck/done/pending.",
    "Ensure every interactive + key informational element keeps/has data-testid attributes (kebab-case).",
    "Do not use transition: all anywhere."
  ]
}

---

<General UI UX Design Guidelines>  
    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms
    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text
   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json

 **GRADIENT RESTRICTION RULE**
NEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc
NEVER use dark gradients for logo, testimonial, footer etc
NEVER let gradients cover more than 20% of the viewport.
NEVER apply gradients to text-heavy content or reading areas.
NEVER use gradients on small UI elements (<100px width).
NEVER stack multiple gradient layers in the same viewport.

**ENFORCEMENT RULE:**
    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors

**How and where to use:**
   • Section backgrounds (not content backgrounds)
   • Hero section header content. Eg: dark to light to dark color
   • Decorative overlays and accent elements only
   • Hero section with 2-3 mild color
   • Gradients creation can be done for any angle say horizontal, vertical or diagonal

- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**

</Font Guidelines>

- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. 
   
- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.

- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.
   
- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly
    Eg: - if it implies playful/energetic, choose a colorful scheme
           - if it implies monochrome/minimal, choose a black–white/neutral scheme

**Component Reuse:**
	- Prioritize using pre-existing components from src/components/ui when applicable
	- Create new components that match the style and conventions of existing components when needed
	- Examine existing components to understand the project's component patterns before creating new ones

**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component

**Best Practices:**
	- Use Shadcn/UI as the primary component library for consistency and accessibility
	- Import path: ./components/[component-name]

**Export Conventions:**
	- Components MUST use named exports (export const ComponentName = ...)
	- Pages MUST use default exports (export default function PageName() {...})

**Toasts:**
  - Use `sonner` for toasts"
  - Sonner component are located in `/app/src/components/ui/sonner.tsx`

Use 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.
</General UI UX Design Guidelines>

{
  "product": {
    "name": "KONNTO AI",
    "tagline": "One calm AI brain for your business — talk, save, and it acts.",
    "brand_attributes": [
      "calm",
      "premium",
      "trustworthy",
      "WhatsApp-native",
      "fast on mobile",
      "no-training-required"
    ],
    "design_personality": {
      "keywords": [
        "messaging-first",
        "quiet confidence",
        "white cards",
        "charcoal text",
      "single deep-teal accent",
        "high-contrast status colors",
        "short sentences",
        "big tap targets"
      ],
      "anti_patterns": [
        "centered-everything layouts",
        "busy gradients",
        "purple accents",
        "tiny icon-only actions",
        "heavy shadows",
        "dense paragraphs",
        "training/tutorial-first onboarding"
      ]
    }
  },

  "global_rules": {
    "language": "English only",
    "pricing_visibility": "Never show prices to customers anywhere in the customer-facing app or landing pages.",
    "mobile_first": {
      "baseline_width": 390,
      "tap_target_min_px": 44,
      "safe_area": "Respect iOS safe-area insets for bottom tab bar and composer."
    },
    "testing": {
      "data_testid_required": "All interactive and key informational elements MUST include data-testid in kebab-case describing role (not appearance).",
      "examples": [
        "data-testid=\"chat-composer-send-button\"",
        "data-testid=\"work-item-status-pill\"",
        "data-testid=\"approvals-allow-once-button\"",
        "data-testid=\"dashboard-overdue-counter\""
      ]
    },
    "gradient_policy": {
      "allowed": [
        "Hero/landing section background only (max 20% viewport)",
        "Decorative overlays (subtle, low saturation)",
        "Never on text-heavy cards"
      ],
      "prohibited": [
        "dark/saturated gradients (purple/pink, blue/purple, red/pink, green/blue)",
        "gradients on small UI elements (<100px)",
        "stacked gradients in same viewport"
      ],
      "enforcement": "If gradient area exceeds 20% of viewport OR impacts readability, fallback to solid colors."
    }
  },

  "typography": {
    "google_fonts": {
      "heading": {
        "family": "Space Grotesk",
        "weights": [500, 600, 700],
        "usage": "Headings, counters, section titles"
      },
      "body": {
        "family": "Inter",
        "weights": [400, 500, 600],
        "usage": "Body, UI labels, chat text"
      }
    },
    "css_font_tokens": {
      "--font-sans": "Inter, ui-sans-serif, system-ui",
      "--font-display": "Space Grotesk, Inter, ui-sans-serif, system-ui"
    },
    "type_scale_tailwind": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight",
      "h2": "text-base md:text-lg font-medium text-muted-foreground",
      "h3": "text-lg font-semibold",
      "body": "text-sm md:text-base leading-6",
      "small": "text-xs text-muted-foreground"
    },
    "copy_rules": {
      "tone": "Short sentences. One idea per line.",
      "chat": "Prefer 1–2 sentence replies. Use bullets for lists.",
      "whatsapp": "Outbound WhatsApp messages: max 3 buttons. Keep under ~280 chars when possible."
    }
  },

  "color_system": {
    "notes": "Light background, white cards, charcoal text, ONE deep-teal accent. Status colors are fixed: amber due, red overdue, grey stuck, green done.",
    "tokens_hsl_for_shadcn_index_css": {
      "--background": "210 20% 98%",
      "--foreground": "222 22% 14%",

      "--card": "0 0% 100%",
      "--card-foreground": "222 22% 14%",

      "--popover": "0 0% 100%",
      "--popover-foreground": "222 22% 14%",

      "--primary": "174 78% 24%",
      "--primary-foreground": "0 0% 100%",

      "--secondary": "210 16% 96%",
      "--secondary-foreground": "222 22% 14%",

      "--muted": "210 16% 96%",
      "--muted-foreground": "215 16% 40%",

      "--accent": "174 40% 92%",
      "--accent-foreground": "174 78% 18%",

      "--destructive": "0 72% 52%",
      "--destructive-foreground": "0 0% 100%",

      "--border": "214 18% 88%",
      "--input": "214 18% 88%",
      "--ring": "174 78% 24%",

      "--radius": "0.9rem",

      "--chart-1": "174 78% 24%",
      "--chart-2": "38 92% 50%",
      "--chart-3": "0 72% 52%",
      "--chart-4": "215 16% 40%",
      "--chart-5": "142 55% 36%"
    },
    "brand_hex_reference": {
      "bg_canvas": "#F7FAFB",
      "text_charcoal": "#1F2937",
      "text_muted": "#5B6776",
      "teal_primary": "#0F766E",
      "teal_soft": "#D7F3EF",
      "border": "#E3E8EF",
      "status": {
        "due_amber": "#F59E0B",
        "overdue_red": "#EF4444",
        "stuck_grey": "#6B7280",
        "done_green": "#16A34A"
      }
    },
    "status_usage": {
      "due": "Amber pill + subtle amber dot. Never use amber as a background for long text.",
      "overdue": "Red pill + red left border on cards.",
      "stuck": "Grey pill + dashed border optional.",
      "done": "Green pill + check icon."
    }
  },

  "layout_and_grid": {
    "app_shell": {
      "mobile": {
        "pattern": "Bottom tab bar (5 tabs). Chat is default.",
        "top_bar": "Sticky top bar with business name + search + profile menu.",
        "content_padding": "px-4 pt-3 pb-[calc(72px+env(safe-area-inset-bottom))]"
      },
      "desktop": {
        "pattern": "Left rail + top bar. Content uses max-w with generous gutters.",
        "rail_width": "w-[280px]",
        "content_max": "max-w-[1120px]",
        "page_padding": "px-6 py-6"
      }
    },
    "landing_page": {
      "grid": "12-col on lg, single column on mobile",
      "hero": "Split layout on lg: left copy + right product mock (chat screenshot). On mobile: copy then mock.",
      "section_spacing": "py-14 md:py-20",
      "card_radius": "rounded-[var(--radius)]",
      "elevation": "Prefer borders over shadows; if needed use shadow-sm only."
    }
  },

  "components": {
    "component_path": {
      "button": "/app/frontend/src/components/ui/button.jsx",
      "card": "/app/frontend/src/components/ui/card.jsx",
      "badge": "/app/frontend/src/components/ui/badge.jsx",
      "tabs": "/app/frontend/src/components/ui/tabs.jsx",
      "sheet": "/app/frontend/src/components/ui/sheet.jsx",
      "drawer": "/app/frontend/src/components/ui/drawer.jsx",
      "dialog": "/app/frontend/src/components/ui/dialog.jsx",
      "dropdown_menu": "/app/frontend/src/components/ui/dropdown-menu.jsx",
      "input": "/app/frontend/src/components/ui/input.jsx",
      "textarea": "/app/frontend/src/components/ui/textarea.jsx",
      "checkbox": "/app/frontend/src/components/ui/checkbox.jsx",
      "avatar": "/app/frontend/src/components/ui/avatar.jsx",
      "scroll_area": "/app/frontend/src/components/ui/scroll-area.jsx",
      "separator": "/app/frontend/src/components/ui/separator.jsx",
      "command": "/app/frontend/src/components/ui/command.jsx",
      "calendar": "/app/frontend/src/components/ui/calendar.jsx",
      "sonner_toasts": "/app/frontend/src/components/ui/sonner.jsx"
    },

    "buttons": {
      "shape": "Rounded (10–14px). Big, calm. No aggressive gradients.",
      "sizes": {
        "sm": "h-9 px-3 text-sm",
        "md": "h-11 px-4 text-sm",
        "lg": "h-12 px-5 text-base"
      },
      "variants": {
        "primary": "bg-primary text-primary-foreground hover:bg-primary/90 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        "secondary": "bg-secondary text-secondary-foreground hover:bg-secondary/80 border border-border",
        "ghost": "hover:bg-accent hover:text-accent-foreground",
        "destructive": "bg-destructive text-destructive-foreground hover:bg-destructive/90"
      },
      "micro_interactions": {
        "hover": "Only on pointer devices: subtle translate-y-[-1px] + shadow-sm",
        "press": "active:translate-y-0 active:scale-[0.99]",
        "loading": "Inline spinner left of label; keep label width stable"
      }
    },

    "chat": {
      "chat_wall": {
        "background": "Solid very-light canvas (no wallpaper). Optional 4% noise overlay.",
        "container": "max-w-[760px] mx-auto px-4"
      },
      "bubble": {
        "incoming": {
          "classes": "bg-card text-foreground border border-border rounded-2xl rounded-tl-md px-3 py-2 shadow-[0_1px_0_rgba(16,24,40,0.04)]",
          "meta": "timestamp + optional source chips below"
        },
        "outgoing": {
          "classes": "bg-primary/10 text-foreground border border-primary/15 rounded-2xl rounded-tr-md px-3 py-2",
          "meta": "timestamp right aligned"
        },
        "system_notice": {
          "classes": "bg-secondary text-secondary-foreground border border-border rounded-xl px-3 py-2 text-xs"
        }
      },
      "composer": {
        "layout": "Sticky bottom. Left: attach. Center: textarea autosize. Right: mic + send.",
        "classes": "bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 border-t border-border px-3 py-2",
        "textarea": "min-h-[44px] max-h-[140px] resize-none rounded-xl",
        "voice_recording": {
          "state": "When recording: show timer + red dot + Cancel button",
          "timer_style": "font-medium tabular-nums"
        }
      },
      "source_chips": {
        "component": "Badge",
        "classes": "bg-secondary text-secondary-foreground hover:bg-secondary/80 rounded-full",
        "behavior": "Opens source in Sheet (mobile) / side panel (desktop)."
      },
      "proposal_cards": {
        "component": "Card",
        "layout": "Inline under KONNTO reply. Title + key fields + 3 buttons: Save / Edit / Skip.",
        "classes": "border border-border rounded-2xl",
        "buttons_rule": "In WhatsApp outbound: max 3 buttons. In-app proposal card: exactly 3 actions, never more.",
        "save_state": "After Save: show compact confirmation row with Undo (ghost button)."
      },
      "empty_state": {
        "pattern": "Centered vertically but content left-aligned within a max-w card.",
        "suggestion_chips": "Use Badge as clickable chips (ghost/secondary)."
      }
    },

    "status_pills": {
      "base": "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium border",
      "variants": {
        "due": "bg-amber-50 text-amber-800 border-amber-200",
        "overdue": "bg-red-50 text-red-700 border-red-200",
        "stuck": "bg-slate-50 text-slate-700 border-slate-200",
        "done": "bg-emerald-50 text-emerald-700 border-emerald-200"
      },
      "icon": "lucide-react: Clock (due), AlertTriangle (overdue), PauseCircle (stuck), CheckCircle2 (done)"
    },

    "dashboard": {
      "counters": {
        "layout": "2x2 grid on mobile, 4-up on md+",
        "component": "Card",
        "counter_style": "text-2xl font-semibold font-display",
        "label_style": "text-sm text-muted-foreground"
      },
      "who_waiting_on_whom": {
        "component": "Card + Table or stacked rows",
        "row": "Avatar + name + waiting-on + due pill"
      },
      "morning_brief": {
        "component": "Card",
        "style": "Left border in primary/30 + concise bullets"
      }
    },

    "work_list": {
      "filters": {
        "component": "Tabs + Select",
        "pattern": "Sticky filter bar under top bar on mobile"
      },
      "rows": {
        "component": "Card (flat row) or button-like row",
        "row_classes": "flex items-start gap-3 rounded-2xl border border-border bg-card px-3 py-3 hover:bg-accent/40",
        "left": "Status dot + title",
        "right": "Assignee avatar + due date + status pill"
      },
      "detail": {
        "component": "Sheet (mobile) / side panel (desktop)",
        "timeline": "Use Separator + stacked events; keep timestamps tabular-nums",
        "status_change": "Buttons: Done, Delayed, Stuck. Delayed/Stuck require reason textarea."
      }
    },

    "team": {
      "members_list": "Card rows with Avatar + role + access chips + WhatsApp status",
      "add_person": "Dialog with Input + Select role + Checkbox permissions",
      "threads": "WhatsApp-like thread view using same chat bubble system"
    },

    "approvals": {
      "card": {
        "component": "Card",
        "layout": "Request summary + context + 3 actions: Allow once / Always allow / Don’t allow",
        "classes": "rounded-2xl border border-border",
        "always_allow_money": "If money: show Input for ‘under amount’ inline before confirm"
      },
      "reply_in_words": "Textarea under actions; keep short placeholder examples"
    },

    "search": {
      "component": "Command",
      "pattern": "Global search opens Command dialog; results grouped: Work, People, Docs, Rules"
    },

    "documents": {
      "upload": "Use Button + Input type=file hidden; show progress",
      "detail": "Sheet with AI summary (bullets) + key details as definition list"
    },

    "admin_console": {
      "tone": "Desktop-first, denser tables, still calm.",
      "teach_ai": "Tabs: Draft vs Published. Version history table with Restore button.",
      "website_editor": "Form fields in Card sections; Preview panel on right on xl",
      "customers": "Table + usage charts (Recharts)"
    }
  },

  "motion_and_microinteractions": {
    "library": "framer-motion (already available)",
    "principles": [
      "Motion is functional: confirm actions, show state changes, guide attention.",
      "Keep durations short and easing soft.",
      "Respect prefers-reduced-motion."
    ],
    "tokens": {
      "duration_fast_ms": 120,
      "duration_base_ms": 180,
      "duration_slow_ms": 240,
      "easing": "cubic-bezier(0.2, 0.8, 0.2, 1)"
    },
    "patterns": {
      "message_in": "Fade + slight rise (y: 6 -> 0) for new bubbles",
      "proposal_card": "Expand/collapse with height auto animation",
      "save_confirmation": "Slide-in toast (sonner) + inline Undo row",
      "tab_switch": "No page fade; keep instant with subtle underline motion"
    }
  },

  "textures_and_background": {
    "noise": {
      "usage": "Optional subtle noise overlay on app canvas and landing hero only.",
      "css_snippet": ".noise::before { content: \"\"; position: absolute; inset: 0; background-image: url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"120\" height=\"120\"><filter id=\"n\"><feTurbulence type=\"fractalNoise\" baseFrequency=\"0.9\" numOctaves=\"2\" stitchTiles=\"stitch\"/></filter><rect width=\"120\" height=\"120\" filter=\"url(%23n)\" opacity=\"0.06\"/></svg>'); pointer-events: none; mix-blend-mode: multiply; }"
    },
    "hero_gradient": {
      "allowed_example": "bg-[radial-gradient(1200px_circle_at_20%_10%,rgba(15,118,110,0.10),transparent_55%),radial-gradient(900px_circle_at_80%_0%,rgba(15,118,110,0.06),transparent_50%)]",
      "note": "This stays subtle and within the hero only."
    }
  },

  "landing_page_layout": {
    "header": {
      "left": "KONNTO wordmark",
      "right": "Nav: How it works, Security, Help, Sign in + primary CTA Start free",
      "mobile": "Hamburger opens Sheet with same links"
    },
    "hero": {
      "headline": "Talk to KONNTO. It remembers. It acts.",
      "subhead": "Send a message on WhatsApp or in the app. KONNTO turns it into tasks, promises, reminders — and follows up.",
      "ctas": [
        "Start free (primary)",
        "See how it works (secondary)"
      ],
      "proof_row": "3 small items: WhatsApp-first • Source links • One-tap Save",
      "visual": "Product mock: chat + proposal card + approval card"
    },
    "how_it_works": {
      "steps": [
        "Talk",
        "K-BRAIN thinks",
        "It acts"
      ],
      "component": "3 cards with icons + 2 lines each"
    },
    "whatsapp_first": {
      "content": "Explain short WhatsApp messages + 3-button limit",
      "example": "Show a WhatsApp-style message preview card"
    },
    "for_any_business": {
      "layout": "Bento grid of industries (Retail, Services, Logistics, Clinics, Agencies, Manufacturing)",
      "note": "No pricing. Focus on outcomes."
    },
    "security_trust": {
      "cards": "Data privacy, permissions, audit trail, export/delete data"
    },
    "final_cta": {
      "headline": "Start with one number.",
      "cta": "Start free",
      "support": "Secondary link: Talk to KONNTO (opens help chat)"
    },
    "footer": {
      "links": ["Terms", "Privacy", "Help"],
      "note": "No pricing links in public footer."
    }
  },

  "auth_and_onboarding": {
    "clerk": {
      "layout": "Centered column. Optional brand side panel visible on lg+ only.",
      "side_panel": "Quiet gradient-less panel with 2 bullets + small product mock.",
      "data_testid": {
        "signin": "auth-signin",
        "signup": "auth-signup"
      }
    },
    "whatsapp_continue": {
      "page": "Phone input + 6-digit OTP (use shadcn input-otp)",
      "components": ["Input", "InputOTP", "Button"],
      "data_testid_examples": [
        "whatsapp-auth-phone-input",
        "whatsapp-auth-send-code-button",
        "whatsapp-auth-otp-input",
        "whatsapp-auth-verify-button"
      ]
    },
    "onboarding_one_question": {
      "question": "What’s your WhatsApp number?",
      "consent": "Checkbox: I agree to receive WhatsApp messages from KONNTO for this business.",
      "cta": "Continue",
      "note": "No tutorials. After submit, open Chat."
    }
  },

  "libraries_and_integrations": {
    "icons": "lucide-react (already installed)",
    "toasts": "sonner via /app/frontend/src/components/ui/sonner.jsx",
    "charts": {
      "library": "recharts",
      "use_cases": ["Admin console usage charts", "Dashboard trends (optional)"]
    },
    "installation_if_missing": {
      "recharts": "npm i recharts",
      "framer_motion": "npm i framer-motion"
    }
  },

  "image_urls": {
    "landing_hero_photography": [
      {
        "url": "https://images.unsplash.com/photo-1659080548656-3c3ffb870950?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA3MDB8MHwxfHNlYXJjaHwxfHxjYWxtJTIwYnVzaW5lc3MlMjBvd25lciUyMHVzaW5nJTIwcGhvbmUlMjBtZXNzYWdpbmclMjBhcHAlMjBsaWdodCUyMGJhY2tncm91bmR8ZW58MHx8fHRlYWx8MTc5NDU3NTQ0NHww&ixlib=rb-4.1.0&q=85",
        "category": "landing",
        "placement": "Hero side image (optional) or testimonial strip",
        "description": "Phone-first business owner vibe; calm, modern"
      },
      {
        "url": "https://images.unsplash.com/photo-1649767821633-f0d6a8c28b51?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA3MDB8MHwxfHNlYXJjaHwyfHxjYWxtJTIwYnVzaW5lc3MlMjBvd25lciUyMHVzaW5nJTIwcGhvbmUlMjBtZXNzYWdpbmclMjBhcHAlMjBsaWdodCUyMGJhY2tncm91bmR8ZW58MHx8fHRlYWx8MTc5NDU3NTQ0NHww&ixlib=rb-4.1.0&q=85",
        "category": "landing",
        "placement": "Use in ‘For any business’ section as subtle human proof",
        "description": "Friendly, global SMB feel"
      }
    ]
  },

  "instructions_to_main_agent": {
    "css_updates": [
      "Replace default shadcn tokens in /app/frontend/src/index.css with the HSL tokens above.",
      "Remove CRA starter styles in /app/frontend/src/App.css (dark centered header). Ensure no .App { text-align:center } is introduced.",
      "Add font imports in public/index.html or via CSS @import; set body font to var(--font-sans) and headings to var(--font-display)."
    ],
    "component_build_notes_js": [
      "This repo uses .jsx (not .tsx). Keep components in .jsx and use prop-types only if project already uses it.",
      "Use shadcn/ui primitives from /src/components/ui for dropdowns, dialogs, sheets, calendar, etc. Do not use raw HTML equivalents.",
      "Every interactive element must include data-testid."
    ],
    "chat_priority": [
      "Chat is home. Make Chat route default after onboarding.",
      "Proposal cards must always show exactly 3 actions: Save / Edit / Skip.",
      "After Save, show inline Undo + sonner toast confirmation."
    ],
    "accessibility": [
      "Ensure focus-visible rings are teal and clearly visible.",
      "Use aria-labels for icon-only buttons (mic, attach, send).",
      "Maintain WCAG AA contrast for status pills and links."
    ]
  }
}

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

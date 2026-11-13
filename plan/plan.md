# KONNTO AI — Launch Plan

KONNTO AI is one AI brain (K-BRAIN) for any business. People just talk to it on WhatsApp or in the app, and it thinks, remembers, replies and gets things done.
It keeps track of tasks, promises, people and approvals, so nothing gets forgotten and everyone knows what to do next.

---

## Who it's for

- **Business owners**, any size, any industry, anywhere.
- **Their team**: everyone who works in the business.
- **Outside partners**: suppliers, contractors and clients. Always free, and WhatsApp is enough for them.
- **KONNTO admin** (tginfrane@gmail.com): runs the platform and teaches the AI.

---

## Core features and experience

### How it works: talk → K-BRAIN thinks → it acts

**1. Talk (in)**
- Type, send a voice note (any language), or send a photo or document.
- Use WhatsApp or the app; both are the same conversation.

**2. K-BRAIN thinks**
- Understands what was said: tasks, promises, dates, people, amounts, requests and questions.
- Remembers everything about the business, and learns as people talk.
- Decides who should know, who should act, and what each person may see.

**3. It acts (out)**
- Replies, with a link to where the answer came from.
- Creates tasks and promises after a one-tap **Save**.
- Messages the right person on WhatsApp.
- Sends reminders and chases late items.
- Asks the owner when something needs permission.
- Sends a morning brief and an evening "anything to remember?"

### Sign-up
- Sign in with Google, email, or WhatsApp.
- The only question asked is the WhatsApp number. KONNTO works out the rest by itself.
- A WhatsApp welcome arrives within a minute; from then on, people just chat.

### The app: one chat screen and four tabs
| Tab | What it does |
|---|---|
| **Chat** (home) | Talk to KONNTO. Tell it, ask it, or tell it to do something ("Tell Ramesh to send the quote by Friday"). |
| **Dashboard** | Today at a glance: due, overdue, stuck, and who is waiting on whom. |
| **Work** | All tasks, projects and promises. |
| **Team** | Everyone in the business and partners. Chat directly or in groups; **Give task**; **Send request** to a supplier. Messages reach people on WhatsApp too. |
| **Approvals** | Anything needing a yes or no: more access, orders, payments, time off, finished work. Buttons: **Allow once**, **Always allow**, **Don't allow**, or just reply in words. |

The profile menu holds documents, what KONNTO knows, settings, help, and the admin console for admins.

### Team and access, decided by the AI
- Add someone by just saying it: "Add Ramesh, he handles purchasing." KONNTO gives the owner an invite link to forward on WhatsApp; Ramesh taps it and he's in.
- KONNTO decides what each person can see from their job, starting small.
- If someone needs more, KONNTO asks the owner. It understands whether the answer means **once** or **always**, and repeats it back with an **Undo** button.
- **Teach KONNTO by talking**: "From now on, always copy accounts on payment reminders." It saves this as a business rule, which can be seen and removed any time.

### Everything else included
- Tasks that depend on each other: when one is done, the next person is told.
- Stuck or late items need a quick reason, and are chased automatically up the line.
- KONNTO spots promises and decisions in chats and offers to save them.
- Documents become searchable, and KONNTO pulls the key details out of them.
- One search across everything, showing only what each person may see.
- Personal notes stay private. Each person can view, export or delete their data.

### Admin console
- **Teach the AI**: its personality, rules, knowledge, FAQs, pricing answers and welcome message. Test changes before publishing, and undo any change.
- **Website text** editing.
- **Plans and prices**, kept hidden from customers for now. Supports flat, per-seat and new categories.
- **Customers**, usage, AI and WhatsApp costs, feedback, and announcements.

---

## User flow

1. Sign up and enter the WhatsApp number.
2. KONNTO says hi on WhatsApp, and the app opens on **Chat**.
3. Say: "Supplier promised stock by Thursday, remind me Wednesday." Tap **Save**.
4. Say: "Add Ramesh, he handles purchasing." Forward the link; Ramesh joins.
5. In **Team**, give Ramesh a task. He taps **Done** on WhatsApp.
6. Ramesh asks to place an order. It lands in **Approvals**, and the owner taps **Always allow under ₹15,000**.
7. Every morning, the brief arrives on WhatsApp. **Dashboard** shows the full picture.

---

## UI/UX feel

- Simple and calm, like a messaging app. Chat comes first, and nothing needs training.
- Light background, white cards, charcoal text, one deep-teal accent colour.
- Clear colours: amber for due, red for overdue, grey for stuck, green for done.
- Big buttons and short sentences, built for phones first and fine on desktop.
- WhatsApp messages are short, with at most three buttons.

---

## Implementation phases

### Phase 1 — MVP (built now)
Everything above:
- sign-up and the WhatsApp welcome
- Chat, Dashboard, Work, Team and Approvals
- team chats that reach WhatsApp, Give task and Send request
- AI-decided access with once / always approvals
- teaching KONNTO by talking
- reminders and briefs
- documents and search
- privacy controls
- the admin console

### Phase 2 — Paid plans and more control
- Pricing page and online payments (Razorpay for India, Stripe for everywhere else).
- Approvals that pass through more than one person, and letting a trusted lead approve.
- Phone push notifications, and WhatsApp messages in more languages.

### Phase 3 — Insights and growth
- A report on why work gets delayed, and what it costs.
- Weekly and monthly progress reports as PDF.
- Connections to calendar, accounting and CRM tools when customers ask.
- A business's own WhatsApp number, bigger-company features, and phone apps if needed.

---

## Assumptions

- **One shared KONNTO AI WhatsApp number** for all businesses. It needs your Meta WhatsApp Business account, number, access token and app secret, plus Meta's approval of KONNTO's standard messages. Until then, Meta's free test number reaches up to 5 phones, and everything else works in the app and by email.
- **Consent**: KONNTO only messages people who agreed — the owner at sign-up, and team or partners when they tap the invite link and send the join message.
- **AI**: Claude, with voice notes transcribed by OpenAI's Whisper. Both run on Emergent's built-in key, paid from your Emergent balance. Meta's WhatsApp fees go to your Meta account.
- **Email** goes out as "KONNTO AI" through Emergent's email service, only as a backup channel.
- **English screens**; KONNTO replies in the language people use.
- **Free during launch.** No prices are shown yet, and the admin sets hidden usage limits.
- **Sensitive things are never given automatically**: owner-level access, money records, staff details and personal notes. These are always asked.
- **Approvals only record and notify.** KONNTO never moves money.
- **One-to-one team chats are private** to the two people in them.
- **Reminders arrive within 15 minutes** of their set time; chats are instant.
- **The admin can change all platform settings and the AI**, but cannot read customers' business data.
- **Terms and Privacy pages** ship as simple drafts for a lawyer to review.

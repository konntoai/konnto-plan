import { Link } from "react-router-dom";
import { Logo } from "@/components/common";

function LegalLayout({ title, children }) {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="mx-auto max-w-3xl px-4 h-16 flex items-center justify-between">
          <Link to="/"><Logo /></Link>
          <Link to="/" className="text-sm text-muted-foreground hover:text-foreground">Back home</Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-10">
        <div className="rounded-xl border border-amber-200 bg-amber-50 text-amber-900 text-sm px-4 py-3 mb-6" data-testid="legal-draft-note">
          Draft for legal review. This text is a starting point and will be finalised before paid plans launch.
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        <div className="mt-6 space-y-5 text-[15px] leading-7 text-foreground/90">{children}</div>
      </main>
    </div>
  );
}

export function TermsPage() {
  return (
    <LegalLayout title="Terms of Service">
      <p>KONNTO AI (“KONNTO”) provides an AI assistant that helps businesses track tasks, promises, reminders and approvals through WhatsApp and a web app.</p>
      <h2 className="text-lg font-semibold">1. Your account</h2>
      <p>You are responsible for the people you add to your business and the access you give them. Keep your sign-in details safe.</p>
      <h2 className="text-lg font-semibold">2. Acceptable use</h2>
      <p>Only message people who agreed to hear from your business. Do not use KONNTO for spam, unlawful content or to impersonate others.</p>
      <h2 className="text-lg font-semibold">3. AI output</h2>
      <p>KONNTO uses AI to understand messages. It can make mistakes. Check important details before relying on them. KONNTO records approvals and sends notifications; it never moves money.</p>
      <h2 className="text-lg font-semibold">4. Free during launch</h2>
      <p>KONNTO is free during launch, with fair-use limits. Paid plans may be introduced later; you will not be charged without agreeing first. Partners such as suppliers and contractors are always free.</p>
      <h2 className="text-lg font-semibold">5. WhatsApp</h2>
      <p>WhatsApp messages are sent through the official WhatsApp Business Platform. Reply STOP at any time to stop receiving them.</p>
      <h2 className="text-lg font-semibold">6. Changes and contact</h2>
      <p>We may update these terms and will tell you about important changes in the app. Questions? Use Help in the app.</p>
    </LegalLayout>
  );
}

export function PrivacyPolicyPage() {
  return (
    <LegalLayout title="Privacy Policy">
      <p>This policy explains what KONNTO AI collects and how it is used.</p>
      <h2 className="text-lg font-semibold">What we collect</h2>
      <p>Your name, email, WhatsApp number, the messages, voice notes, photos and documents you send to KONNTO, and the tasks, promises and approvals created from them.</p>
      <h2 className="text-lg font-semibold">How we use it</h2>
      <p>To run KONNTO for your business: understanding messages with AI (Anthropic Claude; voice notes transcribed with OpenAI Whisper), reminders, briefs and notifications by WhatsApp and email.</p>
      <h2 className="text-lg font-semibold">Who can see it</h2>
      <p>Only people in your business, and only what their access allows. Personal notes and one-to-one chats are private to the people in them. KONNTO staff can manage platform settings but do not read your business content.</p>
      <h2 className="text-lg font-semibold">Your choices</h2>
      <p>You can view, export or delete your data from Privacy &amp; my data in the app. Reply STOP on WhatsApp to stop messages.</p>
      <h2 className="text-lg font-semibold">Security</h2>
      <p>Files are stored privately and only served to signed-in people with access. Access to sensitive information is never given automatically.</p>
    </LegalLayout>
  );
}

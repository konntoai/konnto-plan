import { Link } from "react-router-dom";
import { SignIn, SignUp } from "@clerk/react";
import { MessageCircle, CheckCircle2 } from "lucide-react";
import { Logo } from "@/components/common";
import { Button } from "@/components/ui/button";

function AuthLayout({ children, mode }) {
  return (
    <div className="min-h-screen bg-background grid lg:grid-cols-2">
      <aside className="hidden lg:flex flex-col justify-between p-10 bg-card border-r border-border hero-glow">
        <Link to="/"><Logo /></Link>
        <div className="max-w-md">
          <h2 className="text-3xl font-semibold tracking-tight">Just talk. KONNTO keeps track.</h2>
          <ul className="mt-6 space-y-3 text-muted-foreground">
            {["Tasks, promises and reminders from one message", "Your team and suppliers on WhatsApp", "Approvals with Allow once, Always allow, Don't allow"].map((t) => (
              <li key={t} className="flex gap-2"><CheckCircle2 className="h-5 w-5 text-primary shrink-0" />{t}</li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-muted-foreground">Free during launch. Partners are always free.</p>
      </aside>
      <main className="flex flex-col items-center justify-center px-4 py-10">
        <Link to="/" className="lg:hidden mb-6"><Logo /></Link>
        {children}
        <div className="mt-6 w-full max-w-[400px] flex flex-col items-center gap-3">
          <div className="flex items-center gap-3 w-full text-xs text-muted-foreground"><span className="h-px flex-1 bg-border" />or<span className="h-px flex-1 bg-border" /></div>
          <Button asChild variant="outline" className="w-full" data-testid={`${mode}-whatsapp-button`}>
            <Link to="/login/whatsapp"><MessageCircle className="h-4 w-4 text-[#16A34A]" /> Continue with WhatsApp</Link>
          </Button>
          <p className="text-xs text-muted-foreground text-center">By continuing you agree to the <Link to="/terms" className="underline">Terms</Link> and <Link to="/privacy-policy" className="underline">Privacy Policy</Link>.</p>
        </div>
      </main>
    </div>
  );
}

export function SignInPage() {
  return (
    <AuthLayout mode="signin">
      <div data-testid="auth-signin"><SignIn routing="path" path="/sign-in" signUpUrl="/sign-up" withSignUp /></div>
    </AuthLayout>
  );
}

export function SignUpPage() {
  return (
    <AuthLayout mode="signup">
      <div data-testid="auth-signup"><SignUp routing="path" path="/sign-up" signInUrl="/sign-in" /></div>
    </AuthLayout>
  );
}

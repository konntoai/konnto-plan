import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import ClerkAuthProvider from "@/components/auth/ClerkAuthProvider";
import { RequireAuth } from "@/components/auth/session";
import { MeProvider } from "@/context/MeContext";
import { ThemeProvider } from "@/context/ThemeContext";
import Landing from "@/pages/Landing";
import { TermsPage, PrivacyPolicyPage } from "@/pages/Legal";
import { SignInPage, SignUpPage } from "@/pages/AuthPages";
import WhatsAppLogin from "@/pages/WhatsAppLogin";
import Onboarding from "@/pages/Onboarding";
import Join from "@/pages/Join";
import AppShell from "@/components/AppShell";
import ChatPage from "@/pages/app/Chat";
import DashboardPage from "@/pages/app/Dashboard";
import WorkPage from "@/pages/app/Work";
import PCMPage from "@/pages/app/PCM";
import TeamPage from "@/pages/app/Team";
import ThreadPage from "@/pages/app/Thread";
import ApprovalsPage from "@/pages/app/Approvals";
import DocumentsPage from "@/pages/app/Documents";
import KnowledgePage from "@/pages/app/Knowledge";
import SettingsPage from "@/pages/app/Settings";
import PrivacyPage from "@/pages/app/Privacy";
import HelpPage from "@/pages/app/Help";
import AdminLayout from "@/pages/admin/AdminLayout";
import AdminBrain from "@/pages/admin/AdminBrain";
import AdminSite from "@/pages/admin/AdminSite";
import AdminPlans from "@/pages/admin/AdminPlans";
import AdminCustomers from "@/pages/admin/AdminCustomers";
import AdminFeedback from "@/pages/admin/AdminFeedback";
import AdminSettings from "@/pages/admin/AdminSettings";

const Private = ({ children }) => (
  <RequireAuth>
    <MeProvider>{children}</MeProvider>
  </RequireAuth>
);

function App() {
  return (
    <ThemeProvider>
    <div className="App">
      <BrowserRouter>
        <ClerkAuthProvider>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
            <Route path="/sign-in/*" element={<SignInPage />} />
            <Route path="/sign-up/*" element={<SignUpPage />} />
            <Route path="/login/whatsapp" element={<WhatsAppLogin />} />
            <Route path="/join/:token" element={<Join />} />
            <Route path="/onboarding" element={<Private><Onboarding /></Private>} />
            <Route path="/app" element={<Private><AppShell /></Private>}>
              <Route index element={<Navigate to="chat" replace />} />
              <Route path="chat" element={<ChatPage />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="work" element={<WorkPage />} />
              <Route path="pcm" element={<PCMPage />} />
              <Route path="team" element={<TeamPage />} />
              <Route path="team/thread/:threadId" element={<ThreadPage />} />
              <Route path="approvals" element={<ApprovalsPage />} />
              <Route path="documents" element={<DocumentsPage />} />
              <Route path="knowledge" element={<KnowledgePage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="privacy" element={<PrivacyPage />} />
              <Route path="help" element={<HelpPage />} />
            </Route>
            <Route path="/admin" element={<Private><AdminLayout /></Private>}>
              <Route index element={<AdminBrain />} />
              <Route path="site" element={<AdminSite />} />
              <Route path="plans" element={<AdminPlans />} />
              <Route path="customers" element={<AdminCustomers />} />
              <Route path="feedback" element={<AdminFeedback />} />
              <Route path="settings" element={<AdminSettings />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ClerkAuthProvider>
      </BrowserRouter>
      <Toaster position="top-center" closeButton />
    </div>
    </ThemeProvider>
  );
}

export default App;

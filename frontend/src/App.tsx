import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AuthPage } from "./pages/AuthPage";
import { VerifyEmailPage } from "./pages/VerifyEmailPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { ChatsPage } from "./pages/ChatsPage";
import { ChatPage } from "./pages/ChatPage";
import { ProfilePage } from "./pages/ProfilePage";
import { UserProfilePage } from "./pages/UserProfilePage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { AuthProvider } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import { ChatsProvider } from "./chats/ChatsContext";

function App() {
  return (
    <AuthProvider>
      <ChatsProvider>
        <Layout>
          <Routes>
            <Route path="/auth" element={<AuthPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route
              path="/chats"
              element={
                <RequireAuth>
                  <ChatsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/chats/:chatId"
              element={
                <RequireAuth>
                  <ChatPage />
                </RequireAuth>
              }
            />
            <Route
              path="/profile"
              element={
                <RequireAuth>
                  <ProfilePage />
                </RequireAuth>
              }
            />
            <Route
              path="/users/:userId"
              element={
                <RequireAuth>
                  <UserProfilePage />
                </RequireAuth>
              }
            />
            <Route
              path="/notifications"
              element={
                <RequireAuth>
                  <NotificationsPage />
                </RequireAuth>
              }
            />
            <Route path="/" element={<Navigate to="/chats" replace />} />
            <Route path="*" element={<Navigate to="/chats" replace />} />
          </Routes>
        </Layout>
      </ChatsProvider>
    </AuthProvider>
  );
}

export default App;

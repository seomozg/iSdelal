import { useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { useEffect } from "react";

export default function Login() {
  const { login, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard");
    }
  }, [isAuthenticated, navigate]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="max-w-md w-full p-8 bg-card rounded-2xl shadow-lg border border-border text-center">
        <h1 className="text-2xl font-bold mb-2 text-foreground">Welcome to iSdelal</h1>
        <p className="text-muted-foreground mb-8">Sign in to manage your AI widgets</p>

        <button
          onClick={login}
          className="w-full flex items-center justify-center gap-3 px-6 py-3 border border-border rounded-lg hover:bg-secondary transition-colors text-foreground"
        >
          <svg width="20" height="20" viewBox="0 0 20 20">
            <path d="M19.6 10.23c0-.82-.07-1.42-.2-2.05H10v3.72h5.5c-.24 1.26-.93 2.33-1.97 3.05l3.19 2.47c1.86-1.72 2.93-4.25 2.93-7.19z" fill="#4285F4"/>
            <path d="M10 20c2.7 0 4.96-.89 6.62-2.42l-3.19-2.47c-.89.6-2.02.96-3.43.96-2.64 0-4.87-1.78-5.67-4.18L1.1 14.05C2.78 17.56 6.13 20 10 20z" fill="#34A853"/>
            <path d="M4.33 11.89c-.2-.6-.32-1.24-.32-1.89s.11-1.29.32-1.89L1.1 5.95C.4 7.35 0 8.88 0 10.5s.4 3.15 1.1 4.55l3.23-2.66z" fill="#FBBC05"/>
            <path d="M10 3.83c1.47 0 2.78.51 3.82 1.5l2.86-2.86C14.96.89 12.7 0 10 0 6.13 0 2.78 2.44 1.1 5.95l3.23 2.66C5.13 5.61 7.36 3.83 10 3.83z" fill="#EA4335"/>
          </svg>
          Sign in with Google
        </button>
      </div>
    </div>
  );
}
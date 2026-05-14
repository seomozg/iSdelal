import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";

interface User {
  id: number;
  email: string;
  name: string | null;
  avatar_url: string | null;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: () => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  loading: true,
  login: () => {},
  logout: () => {},
  isAuthenticated: false,
});

const API_BASE = import.meta.env.VITE_API_BASE || "";
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "396621788757-qed19nu6sheoo8119slsbeqa2kor6436.apps.googleusercontent.com";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const initialised = useCallback(() => {
    setLoading(false);
  }, []);

  // Load token from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem("isdelal_token");
    if (savedToken) {
      setToken(savedToken);
      fetchUser(savedToken).catch(() => {
        localStorage.removeItem("isdelal_token");
        setToken(null);
        setUser(null);
        initialised();
      });
    } else {
      initialised();
    }
  }, []);

  async function fetchUser(jwt: string) {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${jwt}` },
    });
    if (!res.ok) throw new Error("Invalid token");
    const data = await res.json();
    setUser(data);
    initialised();
  }

  function handleGoogleLogin() {
    // Use Google Identity Services (Sign In With Google)
    if (!window.google?.accounts?.id) {
      const script = document.createElement("script");
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.onload = initGoogleOneTap;
      document.body.appendChild(script);
    } else {
      initGoogleOneTap();
    }
  }

  function initGoogleOneTap() {
    if (window.google?.accounts?.id) {
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleResponse,
        auto_select: false,
      });
      window.google.accounts.id.prompt();
    }
  }

  async function handleGoogleResponse(response: { credential: string }) {
    try {
      const res = await fetch(`${API_BASE}/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credential: response.credential }),
      });

      if (!res.ok) throw new Error("Google auth failed");

      const data = await res.json();
      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem("isdelal_token", data.access_token);
    } catch (err) {
      console.error("Google login error:", err);
    }
  }

  function logout() {
    setUser(null);
    setToken(null);
    localStorage.removeItem("isdelal_token");
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login: handleGoogleLogin,
        logout,
        isAuthenticated: !!user && !!token,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

// Type augmentation for Google
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { client_id: string; callback: (response: { credential: string }) => void; auto_select?: boolean }) => void;
          prompt: () => void;
        };
      };
    };
  }
}
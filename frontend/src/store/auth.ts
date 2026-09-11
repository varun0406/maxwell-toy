/**
 * Auth store — memory-only. Zero data persisted to device.
 * Every app launch requires a fresh login.
 */
import { create } from 'zustand';

interface AuthState {
  accessToken: string | null;
  user: { id: number; username: string; email?: string } | null;
  setTokens: (access: string, _refresh: string) => void;
  setUser: (user: AuthState['user']) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

// Wipe any previously persisted data from localStorage on module load
try { localStorage.removeItem('maxwell-auth'); } catch {}

export const useAuthStore = create<AuthState>()((set, get) => ({
  accessToken: null,
  user: null,
  // refresh token intentionally ignored — no persistence
  setTokens: (access) => set({ accessToken: access }),
  setUser: (user) => set({ user }),
  logout: () => {
    set({ accessToken: null, user: null });
    // Also clear unlock flag so user must re-enter calculator code
    sessionUnlocked = false;
  },
  isAuthenticated: () => !!get().accessToken,
}));

// ── In-memory unlock flag (cleared on app close / reload) ──────────────────
let sessionUnlocked = false;

export const setUnlocked = () => { sessionUnlocked = true; };
export const getUnlocked = () => sessionUnlocked;

'use client';

/* ──────────────────────────────────────────────
   WaveMash — Auth Context (Google OAuth + YouTube Data Scope)
   ────────────────────────────────────────────── */

import React, { createContext, useContext, useEffect, useState } from 'react';
import { getSupabase } from '@/lib/supabase';
import { Session, User } from '@supabase/supabase-js';
import api from '@/lib/api';
import { UserProfile } from '@/lib/types';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  profile: UserProfile | null;
  googleAccessToken: string | null;
  loading: boolean;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  setGoogleAccessToken: (token: string | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [googleAccessToken, setGoogleAccessTokenState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const setGoogleAccessToken = (token: string | null) => {
    setGoogleAccessTokenState(token);
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('wavemash_yt_token', token);
      } else {
        localStorage.removeItem('wavemash_yt_token');
      }
    }
  };

  const fetchProfile = async (userId: string) => {
    try {
      const sb = getSupabase();
      const { data, error } = await sb
        .from('profiles')
        .select('*')
        .eq('user_id', userId)
        .single();

      if (error) {
        console.warn('Profile fetch note:', error.message);
      } else if (data) {
        setProfile(data as UserProfile);
      }
    } catch (err) {
      console.error('Failed to fetch profile', err);
    }
  };

  const refreshProfile = async () => {
    if (user) {
      await fetchProfile(user.id);
    }
  };

  useEffect(() => {
    if (typeof window === 'undefined') {
      setLoading(false);
      return;
    }

    // 캐시된 토큰 로드
    const cachedToken = localStorage.getItem('wavemash_yt_token');
    if (cachedToken) {
      setGoogleAccessTokenState(cachedToken);
    }

    const sb = getSupabase();

    const initializeAuth = async () => {
      try {
        const { data: { session: currentSession } } = await sb.auth.getSession();

        if (currentSession) {
          setSession(currentSession);
          setUser(currentSession.user);
          api.setAuthToken(currentSession.access_token);

          if (currentSession.provider_token) {
            setGoogleAccessToken(currentSession.provider_token);
          }

          await fetchProfile(currentSession.user.id);
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();

    const { data: { subscription } } = sb.auth.onAuthStateChange(
      async (event, currentSession) => {
        setSession(currentSession);
        setUser(currentSession?.user || null);

        if (currentSession) {
          api.setAuthToken(currentSession.access_token);
          if (currentSession.provider_token) {
            setGoogleAccessToken(currentSession.provider_token);
          }
          await fetchProfile(currentSession.user.id);
        } else {
          api.setAuthToken(null);
          setProfile(null);
          setGoogleAccessToken(null);
        }
        setLoading(false);
      }
    );

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const signInWithGoogle = async () => {
    const sb = getSupabase();
    const { error } = await sb.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/`,
        scopes: 'https://www.googleapis.com/auth/youtube.readonly email profile',
        queryParams: {
          access_type: 'offline',
          prompt: 'consent',
        },
      },
    });
    if (error) throw error;
  };

  const signOut = async () => {
    const sb = getSupabase();
    await sb.auth.signOut();
    setGoogleAccessToken(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        profile,
        googleAccessToken,
        loading,
        signInWithGoogle,
        signOut,
        refreshProfile,
        setGoogleAccessToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

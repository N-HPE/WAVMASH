'use client';

/* ──────────────────────────────────────────────
   WaveMash — Auth Context (Google OAuth — login only)
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
  loading: boolean;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

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

    const sb = getSupabase();

    const initializeAuth = async () => {
      try {
        const { data: { session: currentSession } } = await sb.auth.getSession();

        if (currentSession) {
          setSession(currentSession);
          setUser(currentSession.user);
          api.setAuthToken(currentSession.access_token);
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
      async (_event, currentSession) => {
        setSession(currentSession);
        setUser(currentSession?.user || null);

        if (currentSession) {
          api.setAuthToken(currentSession.access_token);
          await fetchProfile(currentSession.user.id);
        } else {
          api.setAuthToken(null);
          setProfile(null);
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
      },
    });
    if (error) throw error;
  };

  const signOut = async () => {
    const sb = getSupabase();
    await sb.auth.signOut();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        profile,
        loading,
        signInWithGoogle,
        signOut,
        refreshProfile,
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

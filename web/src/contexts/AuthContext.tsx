'use client';

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
  signIn: () => void;
  signUp: () => void;
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
        console.error('Error fetching profile:', error);
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
    // 클라이언트 사이드에서만 실행
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
      async (event, currentSession) => {
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

  const signIn = () => {
    // Handled by the login page
  };

  const signUp = () => {
    // Handled by the login page
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
        signIn,
        signUp,
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

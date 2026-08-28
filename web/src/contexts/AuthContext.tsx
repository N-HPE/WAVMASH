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

function profileFromGoogleUser(authUser: User): Omit<UserProfile, 'track_count' | 'friend_count'> & {
  track_count?: number;
  friend_count?: number;
} {
  const meta = authUser.user_metadata || {};
  const emailPrefix = (authUser.email || 'user').split('@')[0] || 'user';
  const username = `${emailPrefix}_${authUser.id.slice(0, 4)}`;
  return {
    user_id: authUser.id,
    username,
    display_name: (meta.full_name as string) || (meta.name as string) || emailPrefix,
    bio: '',
    avatar_url: (meta.avatar_url as string) || (meta.picture as string) || '',
    favorite_genre: '',
    is_public: true,
    track_count: 0,
    friend_count: 0,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const ensureProfile = async (authUser: User) => {
    try {
      const sb = getSupabase();
      const { data: existing, error: readError } = await sb
        .from('profiles')
        .select('*')
        .eq('user_id', authUser.id)
        .maybeSingle();

      if (readError) {
        console.warn('Profile read note:', readError.message);
      }

      const fromGoogle = profileFromGoogleUser(authUser);

      if (existing) {
        const needsAvatar =
          !existing.avatar_url && fromGoogle.avatar_url;
        const needsName =
          (!existing.display_name || existing.display_name === 'User') &&
          fromGoogle.display_name;

        if (needsAvatar || needsName) {
          const { data: updated } = await sb
            .from('profiles')
            .update({
              ...(needsAvatar ? { avatar_url: fromGoogle.avatar_url } : {}),
              ...(needsName ? { display_name: fromGoogle.display_name } : {}),
            })
            .eq('user_id', authUser.id)
            .select('*')
            .maybeSingle();
          if (updated) {
            setProfile(updated as UserProfile);
            return;
          }
        }
        setProfile(existing as UserProfile);
        return;
      }

      const { data: created, error: insertError } = await sb
        .from('profiles')
        .insert(fromGoogle)
        .select('*')
        .maybeSingle();

      if (created) {
        setProfile(created as UserProfile);
        return;
      }

      if (insertError) {
        console.warn('Profile create note:', insertError.message);
        try {
          const me = await api.getMyProfile();
          setProfile(me);
        } catch {
          setProfile({
            ...fromGoogle,
            track_count: 0,
            friend_count: 0,
          } as UserProfile);
        }
      }
    } catch (err) {
      console.error('Failed to ensure profile', err);
    }
  };

  const fetchProfile = async (authUser: User) => {
    await ensureProfile(authUser);
  };

  const refreshProfile = async () => {
    if (user) {
      await fetchProfile(user);
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
          await fetchProfile(currentSession.user);
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
          await fetchProfile(currentSession.user);
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

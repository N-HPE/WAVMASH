import type { User } from '@supabase/supabase-js';
import type { UserProfile } from '@/lib/types';

/** 로그인 사용자의 프로필 페이지 경로 */
export function getProfileHref(
  user: User | null | undefined,
  profile: UserProfile | null | undefined
): string {
  if (!user) return '/login';
  if (profile?.username) return `/profile/${encodeURIComponent(profile.username)}`;
  return '/profile/me';
}

/** URL 세그먼트가 본인 프로필인지 (me 또는 user id) */
export function isOwnProfileSegment(
  segment: string,
  user: User | null | undefined,
  profile: UserProfile | null | undefined
): boolean {
  if (!user || !segment) return false;
  if (segment === 'me') return true;
  if (segment === user.id) return true;
  if (profile?.username && segment === profile.username) return true;
  return false;
}

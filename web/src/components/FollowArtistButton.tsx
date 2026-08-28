'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { UserPlus, UserCheck } from 'lucide-react';
import api from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

type Size = 'sm' | 'xs';

interface FollowArtistButtonProps {
  artistId: string;
  artistName?: string;
  artistImageUrl?: string;
  size?: Size;
  className?: string;
  /** 검색 카드처럼 링크 안에 넣을 때 클릭이 네비게이션으로 새지 않게 */
  stopPropagation?: boolean;
}

export default function FollowArtistButton({
  artistId,
  artistName = '',
  artistImageUrl = '',
  size = 'sm',
  className,
  stopPropagation = false,
}: FollowArtistButtonProps) {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [following, setFollowing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!user || !artistId) {
      setFollowing(false);
      setReady(true);
      return;
    }
    let cancelled = false;
    setReady(false);
    api
      .getArtistFollowStatus(artistId)
      .then((res) => {
        if (!cancelled) setFollowing(Boolean(res.following));
      })
      .catch(() => {
        if (!cancelled) setFollowing(false);
      })
      .finally(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, [artistId, user, authLoading]);

  const onClick = async (e: React.MouseEvent) => {
    if (stopPropagation) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (!user) {
      router.push('/login');
      return;
    }
    if (busy || !artistId) return;
    setBusy(true);
    const prev = following;
    setFollowing(!prev);
    try {
      if (prev) {
        await api.unfollowArtist(artistId);
      } else {
        await api.followArtist(artistId, {
          artist_name: artistName,
          artist_image_url: artistImageUrl,
        });
      }
    } catch {
      setFollowing(prev);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Button
      type="button"
      variant={following ? 'secondary' : 'default'}
      size={size === 'xs' ? 'xs' : 'sm'}
      disabled={busy || (!ready && Boolean(user))}
      onClick={onClick}
      className={cn(
        following && 'text-muted-foreground',
        className
      )}
      aria-pressed={following}
    >
      {following ? (
        <UserCheck className="shrink-0" />
      ) : (
        <UserPlus className="shrink-0" />
      )}
      {following ? '팔로잉' : '팔로우'}
    </Button>
  );
}

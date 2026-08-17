'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import api from '@/lib/api';
import { UserProfile } from '@/lib/types';
import { motion } from 'framer-motion';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';

export default function ProfilePage() {
  const params = useParams();
  const username = params.username as string;
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const data = await api.getProfile(username);
        setProfile(data);
      } catch (err: any) {
        setError(err.message || '프로필을 불러오지 못했습니다.');
      } finally {
        setLoading(false);
      }
    };

    if (username) {
      fetchProfile();
    }
  }, [username]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        <div className="flex items-center space-x-6">
          <Skeleton className="h-24 w-24 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-center text-muted-foreground">{error || '사용자를 찾을 수 없습니다.'}</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Profile Header */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-strong border border-white/[0.06] bg-white/[0.03] rounded-2xl p-6 md:p-8 mb-8"
      >
        <div className="flex flex-col md:flex-row items-center md:items-start gap-6">
          <div className="w-24 h-24 md:w-32 md:h-32 rounded-full overflow-hidden border-2 border-[#d4a853]/50 bg-black/40 shrink-0">
            {profile.avatar_url ? (
              <img src={profile.avatar_url} alt={profile.display_name} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-4xl text-muted-foreground bg-white/5">
                {profile.display_name?.charAt(0).toUpperCase()}
              </div>
            )}
          </div>

          <div className="flex-1 text-center md:text-left">
            <h1 className="text-3xl font-bold mb-1">{profile.display_name}</h1>
            <p className="text-muted-foreground mb-4">@{profile.username}</p>
            
            {profile.bio && (
              <p className="text-sm text-white/80 max-w-lg mb-6">{profile.bio}</p>
            )}

            <div className="flex justify-center md:justify-start gap-6">
              <div className="text-center">
                <div className="text-xl font-semibold text-[#d4a853]">{profile.track_count || 0}</div>
                <div className="text-xs text-muted-foreground">트랙</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-semibold text-[#d4a853]">{profile.friend_count || 0}</div>
                <div className="text-xs text-muted-foreground">친구</div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Profile Tabs */}
      <Tabs defaultValue="collection" className="w-full">
        <TabsList className="w-full bg-white/5 border-b border-white/10 rounded-none justify-start h-auto p-0 mb-6">
          <TabsTrigger value="collection" className="data-[state=active]:bg-transparent data-[state=active]:text-[#d4a853] data-[state=active]:border-b-2 data-[state=active]:border-[#d4a853] rounded-none px-6 py-3">
            컬렉션
          </TabsTrigger>
          <TabsTrigger value="playlists" className="data-[state=active]:bg-transparent data-[state=active]:text-[#d4a853] data-[state=active]:border-b-2 data-[state=active]:border-[#d4a853] rounded-none px-6 py-3">
            플레이리스트
          </TabsTrigger>
          <TabsTrigger value="activity" className="data-[state=active]:bg-transparent data-[state=active]:text-[#d4a853] data-[state=active]:border-b-2 data-[state=active]:border-[#d4a853] rounded-none px-6 py-3">
            활동
          </TabsTrigger>
        </TabsList>

        <TabsContent value="collection" className="mt-0">
          <div className="text-center py-12 text-muted-foreground bg-white/[0.02] border border-white/[0.05] rounded-xl">
            컬렉션이 비어있습니다.
          </div>
        </TabsContent>
        
        <TabsContent value="playlists" className="mt-0">
          <div className="text-center py-12 text-muted-foreground bg-white/[0.02] border border-white/[0.05] rounded-xl">
            공개된 플레이리스트가 없습니다.
          </div>
        </TabsContent>

        <TabsContent value="activity" className="mt-0">
          <div className="text-center py-12 text-muted-foreground bg-white/[0.02] border border-white/[0.05] rounded-xl">
            최근 활동이 없습니다.
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

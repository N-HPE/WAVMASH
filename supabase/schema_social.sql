-- ============================================================================
-- WaveMash Social Community — Supabase Schema v2
-- Extends the base schema with user profiles, social features, and activity feed
-- Run this AFTER the base schema.sql has been applied
-- ============================================================================

-- ═══════════════════════════════════════════════════════════════════════════
-- 1. User Profiles (linked to Supabase Auth)
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT DEFAULT '',
    bio TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    favorite_genre TEXT DEFAULT '',
    track_count INTEGER DEFAULT 0,
    friend_count INTEGER DEFAULT 0,
    is_public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profiles_username ON public.profiles(username);

-- Auto-create profile when a new user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (user_id, username, display_name)
    VALUES (
        NEW.id,
        COALESCE(
            NEW.raw_user_meta_data ->> 'username',
            SPLIT_PART(NEW.email, '@', 1) || '_' || SUBSTR(NEW.id::TEXT, 1, 4)
        ),
        COALESCE(
            NEW.raw_user_meta_data ->> 'display_name',
            NEW.raw_user_meta_data ->> 'full_name',
            NEW.raw_user_meta_data ->> 'name',
            SPLIT_PART(NEW.email, '@', 1)
        )
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- Updated_at trigger for profiles
DROP TRIGGER IF EXISTS set_profiles_updated_at ON public.profiles;
CREATE TRIGGER set_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();


-- ═══════════════════════════════════════════════════════════════════════════
-- 2. Anonymous Collection Tracking
-- ═══════════════════════════════════════════════════════════════════════════

-- Add collector_count to tracks table (cached count of how many users own this track)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tracks' AND column_name = 'collector_count'
    ) THEN
        ALTER TABLE public.tracks ADD COLUMN collector_count INTEGER DEFAULT 0;
    END IF;
END $$;

-- RPC to increment collector count securely without exposing the tracks table to updates
CREATE OR REPLACE FUNCTION public.increment_collector_count(p_track_id TEXT)
RETURNS void AS $$
BEGIN
    UPDATE public.tracks 
    SET collector_count = collector_count + 1
    WHERE track_id = p_track_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC to decrement collector count securely
CREATE OR REPLACE FUNCTION public.decrement_collector_count(p_track_id TEXT)
RETURNS void AS $$
BEGIN
    UPDATE public.tracks 
    SET collector_count = GREATEST(collector_count - 1, 0)
    WHERE track_id = p_track_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ═══════════════════════════════════════════════════════════════════════════
-- 3. Friendships (양방향 친구 관계)
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.friendships (
    user_id UUID NOT NULL REFERENCES public.profiles(user_id) ON DELETE CASCADE,
    friend_id UUID NOT NULL REFERENCES public.profiles(user_id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'blocked')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, friend_id),
    CHECK (user_id <> friend_id)
);

CREATE INDEX IF NOT EXISTS idx_friendships_friend ON public.friendships(friend_id);
CREATE INDEX IF NOT EXISTS idx_friendships_status ON public.friendships(status);

-- Function to update friend_count when friendship is accepted
CREATE OR REPLACE FUNCTION public.update_friend_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.status = 'accepted' THEN
        UPDATE public.profiles SET friend_count = friend_count + 1 WHERE user_id = NEW.user_id;
        UPDATE public.profiles SET friend_count = friend_count + 1 WHERE user_id = NEW.friend_id;
    ELSIF TG_OP = 'UPDATE' AND NEW.status = 'accepted' AND OLD.status = 'pending' THEN
        UPDATE public.profiles SET friend_count = friend_count + 1 WHERE user_id = NEW.user_id;
        UPDATE public.profiles SET friend_count = friend_count + 1 WHERE user_id = NEW.friend_id;
    ELSIF TG_OP = 'DELETE' AND OLD.status = 'accepted' THEN
        UPDATE public.profiles SET friend_count = GREATEST(friend_count - 1, 0) WHERE user_id = OLD.user_id;
        UPDATE public.profiles SET friend_count = GREATEST(friend_count - 1, 0) WHERE user_id = OLD.friend_id;
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_friend_count ON public.friendships;
CREATE TRIGGER trg_update_friend_count
    AFTER INSERT OR UPDATE OR DELETE ON public.friendships
    FOR EACH ROW
    EXECUTE FUNCTION public.update_friend_count();


-- ═══════════════════════════════════════════════════════════════════════════
-- 4. Playlists — Multi-user extension
-- ═══════════════════════════════════════════════════════════════════════════

-- Add owner_id and social fields to existing playlists table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'playlists' AND column_name = 'owner_id'
    ) THEN
        ALTER TABLE public.playlists ADD COLUMN owner_id UUID REFERENCES public.profiles(user_id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'playlists' AND column_name = 'is_public'
    ) THEN
        ALTER TABLE public.playlists ADD COLUMN is_public BOOLEAN DEFAULT TRUE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'playlists' AND column_name = 'description'
    ) THEN
        ALTER TABLE public.playlists ADD COLUMN description TEXT DEFAULT '';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'playlists' AND column_name = 'like_count'
    ) THEN
        ALTER TABLE public.playlists ADD COLUMN like_count INTEGER DEFAULT 0;
    END IF;
END $$;

-- Playlist likes (who liked which playlist)
CREATE TABLE IF NOT EXISTS public.playlist_likes (
    user_id UUID NOT NULL REFERENCES public.profiles(user_id) ON DELETE CASCADE,
    playlist_name TEXT NOT NULL REFERENCES public.playlists(name) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, playlist_name)
);

-- Track likes (WM 내부 곡 좋아요)
CREATE TABLE IF NOT EXISTS public.track_likes (
    user_id UUID NOT NULL REFERENCES public.profiles(user_id) ON DELETE CASCADE,
    track_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, track_id)
);

CREATE INDEX IF NOT EXISTS idx_track_likes_user ON public.track_likes(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_track_likes_track ON public.track_likes(track_id);

-- Track downloads / collections (WM을 통한 곡 다운로드 및 소장)
CREATE TABLE IF NOT EXISTS public.track_downloads (
    user_id UUID NOT NULL REFERENCES public.profiles(user_id) ON DELETE CASCADE,
    track_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, track_id)
);

CREATE INDEX IF NOT EXISTS idx_track_downloads_user ON public.track_downloads(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_track_downloads_track ON public.track_downloads(track_id);



-- ═══════════════════════════════════════════════════════════════════════════
-- 5. Activity Feed
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(user_id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    -- 'added_track', 'created_playlist', 'added_friend', 'liked_playlist', 'shared_playlist'
    target_type TEXT NOT NULL DEFAULT 'track',
    -- 'track', 'playlist', 'user'
    target_id TEXT NOT NULL DEFAULT '',
    metadata JSONB DEFAULT '{}'::jsonb,
    -- Snapshot of relevant data: {title, artist, cover_url, playlist_name, friend_username, ...}
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activities_user ON public.activities(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activities_created ON public.activities(created_at DESC);


-- ═══════════════════════════════════════════════════════════════════════════
-- 6. Row Level Security for new tables
-- ═══════════════════════════════════════════════════════════════════════════

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.friendships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.playlist_likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.track_likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.track_downloads ENABLE ROW LEVEL SECURITY;

-- Track likes: public read, user toggle
DROP POLICY IF EXISTS "Track likes are viewable by everyone" ON public.track_likes;
CREATE POLICY "Track likes are viewable by everyone" ON public.track_likes
    FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS "Users can toggle own track likes" ON public.track_likes;
CREATE POLICY "Users can toggle own track likes" ON public.track_likes
    FOR ALL USING (auth.uid() = user_id);

-- Track downloads: public read, user manage
DROP POLICY IF EXISTS "Track downloads are viewable by everyone" ON public.track_downloads;
CREATE POLICY "Track downloads are viewable by everyone" ON public.track_downloads
    FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS "Users can record own track downloads" ON public.track_downloads;
CREATE POLICY "Users can record own track downloads" ON public.track_downloads
    FOR ALL USING (auth.uid() = user_id);


-- Friendships: involved users can see, sender can create
-- Profiles: anyone can read public profiles, only owner can update
DROP POLICY IF EXISTS "Profiles are viewable by everyone" ON public.profiles;
CREATE POLICY "Profiles are viewable by everyone" ON public.profiles
    FOR SELECT USING (is_public = TRUE OR auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can update own profile" ON public.profiles
    FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own profile" ON public.profiles;
CREATE POLICY "Users can insert own profile" ON public.profiles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Allow the trigger (SECURITY DEFINER) to insert profiles
DROP POLICY IF EXISTS "Service role can insert profiles" ON public.profiles;
CREATE POLICY "Service role can insert profiles" ON public.profiles
    FOR INSERT WITH CHECK (TRUE);

-- Friendships: involved users can see, sender can create
DROP POLICY IF EXISTS "Users can view own friendships" ON public.friendships;
CREATE POLICY "Users can view own friendships" ON public.friendships
    FOR SELECT USING (auth.uid() = user_id OR auth.uid() = friend_id);

DROP POLICY IF EXISTS "Users can create friend requests" ON public.friendships;
CREATE POLICY "Users can create friend requests" ON public.friendships
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update received requests" ON public.friendships;
CREATE POLICY "Users can update received requests" ON public.friendships
    FOR UPDATE USING (auth.uid() = friend_id);

DROP POLICY IF EXISTS "Users can delete own friendships" ON public.friendships;
CREATE POLICY "Users can delete own friendships" ON public.friendships
    FOR DELETE USING (auth.uid() = user_id OR auth.uid() = friend_id);

-- Activities: public feed
DROP POLICY IF EXISTS "Activities are viewable by everyone" ON public.activities;
CREATE POLICY "Activities are viewable by everyone" ON public.activities
    FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS "Users can insert own activities" ON public.activities;
CREATE POLICY "Users can insert own activities" ON public.activities
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Playlist likes
DROP POLICY IF EXISTS "Playlist likes viewable by everyone" ON public.playlist_likes;
CREATE POLICY "Playlist likes viewable by everyone" ON public.playlist_likes
    FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS "Users can like playlists" ON public.playlist_likes;
CREATE POLICY "Users can like playlists" ON public.playlist_likes
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can unlike playlists" ON public.playlist_likes;
CREATE POLICY "Users can unlike playlists" ON public.playlist_likes
    FOR DELETE USING (auth.uid() = user_id);


-- ═══════════════════════════════════════════════════════════════════════════
-- 8. Instagram-Style Collection Feed (Posts, Comments, Likes, Highlights)
-- ═══════════════════════════════════════════════════════════════════════════

-- Posts (Digger's Feed Posts: 사진 + 음악/플리 매칭 감성 포스트)
CREATE TABLE IF NOT EXISTS public.posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(user_id) ON DELETE CASCADE,
    track_id TEXT REFERENCES public.tracks(track_id) ON DELETE CASCADE,
    playlist_id UUID REFERENCES public.playlists(id) ON DELETE SET NULL,
    image_url TEXT DEFAULT '',
    caption TEXT DEFAULT '',
    tags TEXT[] DEFAULT '{}',
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    downloads_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ensure columns exist if table was already created
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'posts' AND column_name = 'image_url') THEN
        ALTER TABLE public.posts ADD COLUMN image_url TEXT DEFAULT '';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'posts' AND column_name = 'playlist_id') THEN
        ALTER TABLE public.posts ADD COLUMN playlist_id UUID REFERENCES public.playlists(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'posts' AND column_name = 'shares_count') THEN
        ALTER TABLE public.posts ADD COLUMN shares_count INTEGER DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'posts' AND column_name = 'downloads_count') THEN
        ALTER TABLE public.posts ADD COLUMN downloads_count INTEGER DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'tracks' AND column_name = 'shares_count') THEN
        ALTER TABLE public.tracks ADD COLUMN shares_count INTEGER DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'tracks' AND column_name = 'likes_count') THEN
        ALTER TABLE public.tracks ADD COLUMN likes_count INTEGER DEFAULT 0;
    END IF;
END $$;



CREATE INDEX IF NOT EXISTS idx_posts_user ON public.posts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_created ON public.posts(created_at DESC);

-- Post Likes
CREATE TABLE IF NOT EXISTS public.post_likes (
    post_id UUID NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(user_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (post_id, user_id)
);

-- Post Comments
CREATE TABLE IF NOT EXISTS public.post_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(user_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_post_comments_post ON public.post_comments(post_id, created_at ASC);

-- Profile Story Highlights (인스타 스토리 큐레이션 하이라이트)
CREATE TABLE IF NOT EXISTS public.highlights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    cover_url TEXT DEFAULT '',
    track_ids TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_highlights_user ON public.highlights(user_id, created_at DESC);

-- Trigger to maintain likes_count on posts
CREATE OR REPLACE FUNCTION public.update_post_likes_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE public.posts SET likes_count = likes_count + 1 WHERE id = NEW.post_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.posts SET likes_count = GREATEST(likes_count - 1, 0) WHERE id = OLD.post_id;
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_post_likes_count ON public.post_likes;
CREATE TRIGGER trg_post_likes_count
    AFTER INSERT OR DELETE ON public.post_likes
    FOR EACH ROW
    EXECUTE FUNCTION public.update_post_likes_count();

-- Trigger to maintain comments_count on posts
CREATE OR REPLACE FUNCTION public.update_post_comments_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE public.posts SET comments_count = comments_count + 1 WHERE id = NEW.post_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.posts SET comments_count = GREATEST(comments_count - 1, 0) WHERE id = OLD.post_id;
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_post_comments_count ON public.post_comments;
CREATE TRIGGER trg_post_comments_count
    AFTER INSERT OR DELETE ON public.post_comments
    FOR EACH ROW
    EXECUTE FUNCTION public.update_post_comments_count();

-- RLS Policies
ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.post_likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.post_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.highlights ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Posts are viewable by everyone" ON public.posts;
CREATE POLICY "Posts are viewable by everyone" ON public.posts
    FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS "Users can insert own posts" ON public.posts;
CREATE POLICY "Users can insert own posts" ON public.posts
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own posts" ON public.posts;
CREATE POLICY "Users can delete own posts" ON public.posts
    FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Post likes are viewable by everyone" ON public.post_likes;
CREATE POLICY "Post likes are viewable by everyone" ON public.post_likes
    FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS "Users can toggle like on posts" ON public.post_likes;
CREATE POLICY "Users can toggle like on posts" ON public.post_likes
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can remove like on posts" ON public.post_likes;
CREATE POLICY "Users can remove like on posts" ON public.post_likes
    FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Comments are viewable by everyone" ON public.post_comments;
CREATE POLICY "Comments are viewable by everyone" ON public.post_comments
    FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS "Users can insert comments" ON public.post_comments;
CREATE POLICY "Users can insert comments" ON public.post_comments
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own comments" ON public.post_comments;
CREATE POLICY "Users can delete own comments" ON public.post_comments
    FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Highlights are viewable by everyone" ON public.highlights;
CREATE POLICY "Highlights are viewable by everyone" ON public.highlights
    FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS "Users can manage own highlights" ON public.highlights;
CREATE POLICY "Users can manage own highlights" ON public.highlights
    FOR ALL USING (auth.uid() = user_id);

-- ═══════════════════════════════════════════════════════════════════════════
-- 9. Account-specific YouTube Playlists & Tracks Database Persistence
-- ═══════════════════════════════════════════════════════════════════════════

-- User YouTube Playlists
CREATE TABLE IF NOT EXISTS public.user_youtube_playlists (
    id TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES public.profiles(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    thumbnail_url TEXT DEFAULT '',
    item_count INTEGER DEFAULT 0,
    is_public BOOLEAN DEFAULT TRUE,
    last_synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, id)
);

CREATE INDEX IF NOT EXISTS idx_user_yt_playlists_user ON public.user_youtube_playlists(user_id, last_synced_at DESC);

-- User YouTube Tracks (Cleaned and Curated items per playlist)
CREATE TABLE IF NOT EXISTS public.user_youtube_tracks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(user_id) ON DELETE CASCADE,
    playlist_id TEXT NOT NULL,
    video_id TEXT NOT NULL,
    raw_title TEXT NOT NULL,
    artist TEXT NOT NULL DEFAULT 'Unknown Artist',
    clean_title TEXT NOT NULL,
    channel_title TEXT DEFAULT '',
    thumbnail_url TEXT DEFAULT '',
    duration TEXT DEFAULT '',
    is_collected BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, playlist_id, video_id)
);

CREATE INDEX IF NOT EXISTS idx_user_yt_tracks_pl ON public.user_youtube_tracks(user_id, playlist_id, created_at ASC);

-- RLS Policies for user YouTube database
ALTER TABLE public.user_youtube_playlists ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_youtube_tracks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own or public youtube playlists" ON public.user_youtube_playlists;
CREATE POLICY "Users can view own or public youtube playlists" ON public.user_youtube_playlists
    FOR SELECT USING (is_public = TRUE OR auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can manage own youtube playlists" ON public.user_youtube_playlists;
CREATE POLICY "Users can manage own youtube playlists" ON public.user_youtube_playlists
    FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can view own or public youtube tracks" ON public.user_youtube_tracks;
CREATE POLICY "Users can view own or public youtube tracks" ON public.user_youtube_tracks
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can manage own youtube tracks" ON public.user_youtube_tracks;
CREATE POLICY "Users can manage own youtube tracks" ON public.user_youtube_tracks
    FOR ALL USING (auth.uid() = user_id);



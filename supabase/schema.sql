-- ============================================================================
-- WaveMash Supabase Schema
-- Dedicated Database Schema for WaveMash (Completely isolated from PIXMASH)
-- ============================================================================

-- 1. Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Tracks Table
CREATE TABLE IF NOT EXISTS public.tracks (
    track_id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    artist TEXT NOT NULL DEFAULT '',
    primary_artist TEXT DEFAULT '',
    album TEXT DEFAULT '',
    genre TEXT DEFAULT 'Unknown',
    year TEXT DEFAULT '',
    bpm TEXT DEFAULT '',
    bpm_num NUMERIC GENERATED ALWAYS AS (
        CASE 
            WHEN bpm ~ '^[0-9]+(\.[0-9]+)?$' THEN bpm::NUMERIC 
            ELSE NULL 
        END
    ) STORED,
    key TEXT DEFAULT '',
    camelot_key TEXT DEFAULT '',
    energy_level INTEGER DEFAULT 0,
    bpm_source TEXT DEFAULT '',
    platform TEXT DEFAULT 'Spotify',
    format TEXT DEFAULT 'WAV',
    url TEXT DEFAULT '',
    external_id TEXT DEFAULT '',
    thumbnail_url TEXT DEFAULT '',
    local_path TEXT DEFAULT '',
    has_cover BOOLEAN DEFAULT FALSE,
    has_file BOOLEAN DEFAULT FALSE,
    dominant_color TEXT DEFAULT NULL,
    analysis JSONB DEFAULT '{}'::jsonb,
    mix_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tracks_artist ON public.tracks(artist);
CREATE INDEX IF NOT EXISTS idx_tracks_album ON public.tracks(album);
CREATE INDEX IF NOT EXISTS idx_tracks_genre ON public.tracks(genre);
CREATE INDEX IF NOT EXISTS idx_tracks_bpm_num ON public.tracks(bpm_num);
CREATE INDEX IF NOT EXISTS idx_tracks_camelot ON public.tracks(camelot_key);
CREATE INDEX IF NOT EXISTS idx_tracks_created_at ON public.tracks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tracks_external_id ON public.tracks(external_id);

-- Full-text search index (Korean / English friendly)
CREATE INDEX IF NOT EXISTS idx_tracks_fts ON public.tracks 
USING GIN (to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(artist, '') || ' ' || coalesce(album, '') || ' ' || coalesce(genre, '')));

-- 3. Playlists Table
CREATE TABLE IF NOT EXISTS public.playlists (
    name TEXT PRIMARY KEY,
    vibe TEXT DEFAULT 'other',
    shade INTEGER DEFAULT 0,
    color TEXT DEFAULT '#6D4C41',
    source TEXT DEFAULT 'local', -- 'local' or 'spotify'
    spotify_url TEXT DEFAULT NULL,
    sync_id TEXT DEFAULT NULL,
    sync_auto BOOLEAN DEFAULT NULL,
    sync_status TEXT DEFAULT NULL,
    last_synced_at TIMESTAMPTZ DEFAULT NULL,
    activity DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    meta JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Playlist Tracks Junction Table (Preserves Track Order)
CREATE TABLE IF NOT EXISTS public.playlist_tracks (
    playlist_name TEXT NOT NULL REFERENCES public.playlists(name) ON DELETE CASCADE,
    track_id TEXT NOT NULL REFERENCES public.tracks(track_id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (playlist_name, track_id)
);

CREATE INDEX IF NOT EXISTS idx_playlist_tracks_pos ON public.playlist_tracks(playlist_name, position ASC);

-- 5. Spotify Sync Configurations Table
CREATE TABLE IF NOT EXISTS public.spotify_sync_configs (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    name TEXT NOT NULL,
    auto_sync_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    sync_deletions BOOLEAN NOT NULL DEFAULT TRUE,
    last_synced_at TEXT DEFAULT NULL,
    track_count INTEGER DEFAULT 0,
    synced_track_ids JSONB DEFAULT '[]'::jsonb,
    status TEXT DEFAULT 'idle',
    local_count INTEGER DEFAULT 0,
    missing_count INTEGER DEFAULT 0,
    missing_ids JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Trigger for updated_at
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_tracks_updated_at ON public.tracks;
CREATE TRIGGER set_tracks_updated_at
    BEFORE UPDATE ON public.tracks
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS set_playlists_updated_at ON public.playlists;
CREATE TRIGGER set_playlists_updated_at
    BEFORE UPDATE ON public.playlists
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS set_spotify_sync_updated_at ON public.spotify_sync_configs;
CREATE TRIGGER set_spotify_sync_updated_at
    BEFORE UPDATE ON public.spotify_sync_configs
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- 7. Row Level Security (RLS)
ALTER TABLE public.tracks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.playlists ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.playlist_tracks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.spotify_sync_configs ENABLE ROW LEVEL SECURITY;

-- Allow public / anon read and write (for personal apps without client-auth restrictions)
DROP POLICY IF EXISTS "Public tracks read" ON public.tracks;
CREATE POLICY "Public tracks read" ON public.tracks FOR SELECT USING (true);

DROP POLICY IF EXISTS "Public tracks insert" ON public.tracks;
CREATE POLICY "Public tracks insert" ON public.tracks FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Public tracks update" ON public.tracks;
CREATE POLICY "Public tracks update" ON public.tracks FOR UPDATE USING (true);

DROP POLICY IF EXISTS "Public tracks delete" ON public.tracks;
CREATE POLICY "Public tracks delete" ON public.tracks FOR DELETE USING (true);

DROP POLICY IF EXISTS "Public playlists read" ON public.playlists;
CREATE POLICY "Public playlists read" ON public.playlists FOR SELECT USING (true);

DROP POLICY IF EXISTS "Public playlists insert" ON public.playlists;
CREATE POLICY "Public playlists insert" ON public.playlists FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Public playlists update" ON public.playlists;
CREATE POLICY "Public playlists update" ON public.playlists FOR UPDATE USING (true);

DROP POLICY IF EXISTS "Public playlists delete" ON public.playlists;
CREATE POLICY "Public playlists delete" ON public.playlists FOR DELETE USING (true);

DROP POLICY IF EXISTS "Public playlist_tracks read" ON public.playlist_tracks;
CREATE POLICY "Public playlist_tracks read" ON public.playlist_tracks FOR SELECT USING (true);

DROP POLICY IF EXISTS "Public playlist_tracks insert" ON public.playlist_tracks;
CREATE POLICY "Public playlist_tracks insert" ON public.playlist_tracks FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Public playlist_tracks update" ON public.playlist_tracks;
CREATE POLICY "Public playlist_tracks update" ON public.playlist_tracks FOR UPDATE USING (true);

DROP POLICY IF EXISTS "Public playlist_tracks delete" ON public.playlist_tracks;
CREATE POLICY "Public playlist_tracks delete" ON public.playlist_tracks FOR DELETE USING (true);

DROP POLICY IF EXISTS "Public spotify_sync read" ON public.spotify_sync_configs;
CREATE POLICY "Public spotify_sync read" ON public.spotify_sync_configs FOR SELECT USING (true);

DROP POLICY IF EXISTS "Public spotify_sync insert" ON public.spotify_sync_configs;
CREATE POLICY "Public spotify_sync insert" ON public.spotify_sync_configs FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Public spotify_sync update" ON public.spotify_sync_configs;
CREATE POLICY "Public spotify_sync update" ON public.spotify_sync_configs FOR UPDATE USING (true);

DROP POLICY IF EXISTS "Public spotify_sync delete" ON public.spotify_sync_configs;
CREATE POLICY "Public spotify_sync delete" ON public.spotify_sync_configs FOR DELETE USING (true);

-- 8. Storage Buckets (Covers & Audio)
INSERT INTO storage.buckets (id, name, public)
VALUES 
    ('wavmash-covers', 'wavmash-covers', true),
    ('wavmash-audio', 'wavmash-audio', false)
ON CONFLICT (id) DO NOTHING;

-- Public Storage Access Policy for Covers
DROP POLICY IF EXISTS "Public cover access" ON storage.objects;
CREATE POLICY "Public cover access" ON storage.objects 
FOR SELECT USING (bucket_id = 'wavmash-covers');

DROP POLICY IF EXISTS "Public cover upload" ON storage.objects;
CREATE POLICY "Public cover upload" ON storage.objects 
FOR INSERT WITH CHECK (bucket_id = 'wavmash-covers');

DROP POLICY IF EXISTS "Public cover update" ON storage.objects;
CREATE POLICY "Public cover update" ON storage.objects 
FOR UPDATE USING (bucket_id = 'wavmash-covers');

DROP POLICY IF EXISTS "Public cover delete" ON storage.objects;
CREATE POLICY "Public cover delete" ON storage.objects 
FOR DELETE USING (bucket_id = 'wavmash-covers');

-- ============================================================================
-- WaveMash Curation Inbox Schema
-- Manages incoming track recommendations from Nexus / Charts for fast audition & triage
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS public.curation_inbox (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    track_id TEXT NOT NULL,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    album TEXT DEFAULT '',
    genre TEXT DEFAULT 'Unknown',
    year TEXT DEFAULT '',
    bpm TEXT DEFAULT '',
    camelot_key TEXT DEFAULT '',
    thumbnail_url TEXT DEFAULT '',
    preview_url TEXT DEFAULT '',
    spotify_url TEXT DEFAULT '',
    youtube_id TEXT DEFAULT '',
    curator TEXT DEFAULT 'nexus_nova', -- 'nexus_nova', 'nexus_briefing', 'chart', 'manual'
    curator_note TEXT DEFAULT '',      -- Recommendation rationale from Nexus
    status TEXT NOT NULL DEFAULT 'inbox', -- 'inbox', 'keep', 'pass', 'downloading', 'archived'
    target_crate TEXT DEFAULT NULL,    -- Designated playlist or crate
    decision_at TIMESTAMPTZ DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for lightning fast querying
CREATE INDEX IF NOT EXISTS idx_curation_status_created ON public.curation_inbox(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_curation_track_id ON public.curation_inbox(track_id);
CREATE INDEX IF NOT EXISTS idx_curation_curator ON public.curation_inbox(curator);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS set_curation_inbox_updated_at ON public.curation_inbox;
CREATE TRIGGER set_curation_inbox_updated_at
    BEFORE UPDATE ON public.curation_inbox
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- RLS Policies
ALTER TABLE public.curation_inbox ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public curation_inbox read" ON public.curation_inbox;
CREATE POLICY "Public curation_inbox read" ON public.curation_inbox FOR SELECT USING (true);

DROP POLICY IF EXISTS "Public curation_inbox insert" ON public.curation_inbox;
CREATE POLICY "Public curation_inbox insert" ON public.curation_inbox FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Public curation_inbox update" ON public.curation_inbox;
CREATE POLICY "Public curation_inbox update" ON public.curation_inbox FOR UPDATE USING (true);

DROP POLICY IF EXISTS "Public curation_inbox delete" ON public.curation_inbox;
CREATE POLICY "Public curation_inbox delete" ON public.curation_inbox FOR DELETE USING (true);

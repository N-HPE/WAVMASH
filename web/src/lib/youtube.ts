/* ──────────────────────────────────────────────
   WaveMash — YouTube Data API Client & Title Cleaner
   meta_parse.py 와 동일 규칙으로 Official/MV/Topic 등 junk 제거
   ────────────────────────────────────────────── */

export interface YouTubePlaylistItem {
  id: string;
  videoId: string;
  title: string;
  artist: string;
  cleanTitle: string;
  channelTitle: string;
  thumbnailUrl: string;
  publishedAt: string;
  duration?: string;
}

export interface YouTubePlaylist {
  id: string;
  title: string;
  description: string;
  thumbnailUrl: string;
  itemCount: number;
  items?: YouTubePlaylistItem[];
}

const JUNK_PAREN =
  /[\(\[【｛{]\s*(?:official(?:\s+(?:music|lyric|audio|video|mv|visualizer))?|official\s*(?:video|audio|mv|hd|4k|visualizer|lyric\s*video)?|music\s*video|lyric\s*video|lyrics?|audio|visualizer|mv|m\/?v|hd|hq|4k|1080p|720p|explicit|clean\s*version|remaster(?:ed)?(?:\s*\d{2,4})?|live(?:\s+(?:at|from|version))?|topic|full\s*album|color\s*coded|eng(?:lish)?(?:\s*\/\s*kor)?|sub(?:title)?s?|karaoke|instrumental\s*only|speed\s*up|slowed|reverb|nightcore|tiktok|shorts?|preview|snippet|clip\s*officiel|videoclip|performance\s*video|prod\.?\s*by|produced\s*by|with\s*lyrics|fan\s*made|audio\s*only|spotify|apple\s*music)[^)\]】｝}]*[\)\]】｝}]/gi;

const JUNK_TRAILING =
  /\s*[-–—|]\s*(?:official(?:\s+(?:music\s*)?(?:video|audio))?|lyrics?|audio|mv|visualizer|remaster(?:ed)?|live|hd|4k|with\s*lyrics)\s*$/i;

const FEAT = /\s*[\(\[]?\s*(?:feat\.?|ft\.?|featuring)\s+([^)\]]+)[\)\]]?/i;

function stripJunk(title: string): string {
  let t = (title || '')
    .replace(/【/g, '[')
    .replace(/】/g, ']')
    .replace(/[「」『』]/g, '')
    .trim();
  let prev = '';
  while (prev !== t) {
    prev = t;
    t = t.replace(JUNK_PAREN, '');
  }
  t = t.replace(JUNK_TRAILING, '');
  return t.replace(/\s{2,}/g, ' ').replace(/^[\s\-–—|·•/"']+|[\s\-–—|·•/"']+$/g, '');
}

function cleanChannel(channel?: string): string {
  if (!channel) return 'Unknown Artist';
  let name = channel.replace(/\s*-\s*topic$/i, '').replace(/vevo$/i, '').trim();
  const stripped = name.replace(/\s*(?:official|music|vevo)\s*$/i, '').trim();
  if (stripped.length >= 2) name = stripped;
  return name || 'Unknown Artist';
}

/**
 * 지저분한 유튜브 제목 → artist / title
 * 예: "Daft Punk - One More Time (Official Video 4K)" → Daft Punk / One More Time
 */
export function cleanYouTubeTitle(
  rawTitle: string,
  channelName?: string
): { artist: string; title: string } {
  const fallback = cleanChannel(channelName);
  const cleaned = stripJunk(rawTitle);
  if (!cleaned) return { artist: fallback, title: 'Unknown' };

  const jp = rawTitle.trim().match(/^(.+?)\s*[「『](.+?)[」』]\s*$/);
  if (jp) {
    return {
      artist: stripJunk(jp[1]) || fallback,
      title: stripJunk(jp[2]) || cleaned,
    };
  }

  const seps = [' - ', ' – ', ' — ', ' | ', ' · ', ' • ', ' / '];
  for (const sep of seps) {
    if (!cleaned.includes(sep)) continue;
    const idx = cleaned.indexOf(sep);
    const left = cleaned.slice(0, idx).trim();
    const right = stripJunk(cleaned.slice(idx + sep.length));
    if (left && right && left.split(/\s+/).length <= 8) {
      let artist = left;
      let title = right;
      const feat = title.match(FEAT);
      if (feat) {
        title = title.replace(FEAT, '').trim();
        if (feat[1] && !artist.toLowerCase().includes(feat[1].toLowerCase())) {
          artist = `${artist}, ${feat[1].trim()}`;
        }
      }
      return { artist, title: title || cleaned };
    }
  }

  const by = cleaned.match(/^(.+?)\s+by\s+(.+)$/i);
  if (by) {
    return { artist: by[2].trim(), title: stripJunk(by[1]) };
  }

  return { artist: fallback, title: cleaned };
}

export async function fetchMyYouTubePlaylists(accessToken: string): Promise<YouTubePlaylist[]> {
  try {
    const res = await fetch(
      'https://www.googleapis.com/youtube/v3/playlists?part=snippet,contentDetails&mine=true&maxResults=50',
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          Accept: 'application/json',
        },
      }
    );

    if (!res.ok) {
      const errText = await res.text();
      console.warn('YouTube Playlists fetch error:', res.status, errText);
      return [];
    }

    const data = await res.json();
    if (!data.items) return [];

    return data.items.map((item: any) => ({
      id: item.id,
      title: item.snippet?.title || 'Untitled Playlist',
      description: item.snippet?.description || '',
      thumbnailUrl:
        item.snippet?.thumbnails?.high?.url ||
        item.snippet?.thumbnails?.medium?.url ||
        item.snippet?.thumbnails?.default?.url ||
        '',
      itemCount: item.contentDetails?.itemCount || 0,
    }));
  } catch (err) {
    console.error('Failed to fetch YouTube playlists:', err);
    return [];
  }
}

export async function fetchPlaylistItems(
  accessToken: string,
  playlistId: string
): Promise<YouTubePlaylistItem[]> {
  try {
    const res = await fetch(
      `https://www.googleapis.com/youtube/v3/playlistItems?part=snippet,contentDetails&playlistId=${encodeURIComponent(
        playlistId
      )}&maxResults=50`,
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          Accept: 'application/json',
        },
      }
    );

    if (!res.ok) return [];

    const data = await res.json();
    if (!data.items) return [];

    return data.items
      .filter((item: any) => item.snippet?.resourceId?.videoId)
      .map((item: any) => {
        const rawTitle = item.snippet?.title || 'Unknown Track';
        const channel =
          item.snippet?.videoOwnerChannelTitle || item.snippet?.channelTitle || '';
        const { artist, title: cleanTitle } = cleanYouTubeTitle(rawTitle, channel);
        const videoId = item.snippet.resourceId.videoId;

        return {
          id: item.id,
          videoId,
          title: rawTitle,
          artist,
          cleanTitle,
          channelTitle: channel,
          thumbnailUrl:
            item.snippet?.thumbnails?.high?.url ||
            item.snippet?.thumbnails?.medium?.url ||
            item.snippet?.thumbnails?.default?.url ||
            `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`,
          publishedAt: item.snippet?.publishedAt || '',
        };
      });
  } catch (err) {
    console.error('Failed to fetch playlist items:', err);
    return [];
  }
}

export async function fetchLikedVideos(accessToken: string): Promise<YouTubePlaylistItem[]> {
  try {
    const res = await fetch(
      'https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails&myRating=like&maxResults=50',
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          Accept: 'application/json',
        },
      }
    );

    if (!res.ok) return [];

    const data = await res.json();
    if (!data.items) return [];

    return data.items.map((item: any) => {
      const rawTitle = item.snippet?.title || 'Unknown Track';
      const channel = item.snippet?.channelTitle || '';
      const { artist, title: cleanTitle } = cleanYouTubeTitle(rawTitle, channel);
      const videoId = item.id;

      return {
        id: item.id,
        videoId,
        title: rawTitle,
        artist,
        cleanTitle,
        channelTitle: channel,
        thumbnailUrl:
          item.snippet?.thumbnails?.high?.url ||
          item.snippet?.thumbnails?.medium?.url ||
          item.snippet?.thumbnails?.default?.url ||
          `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`,
        publishedAt: item.snippet?.publishedAt || '',
      };
    });
  } catch (err) {
    console.error('Failed to fetch liked videos:', err);
    return [];
  }
}

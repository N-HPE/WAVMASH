/* ──────────────────────────────────────────────
   WaveMash — YouTube Data API Client & Title Cleaner
   유튜브 재생목록/좋아요 영상 조회 및 메타데이터 정제 유틸리티
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

/**
 * 지저분한 유튜브 제목에서 아티스트와 순수 곡명을 깔끔하게 분리/정제
 * 예: "Daft Punk - One More Time (Official Video 4K) [Audio]" -> artist: "Daft Punk", title: "One More Time"
 */
export function cleanYouTubeTitle(rawTitle: string, channelName?: string): { artist: string; title: string } {
  let cleaned = rawTitle
    // 괄호 안의 불필요한 메타 텍스트 제거
    .replace(/\s*[\(\[](?:Official\s*(?:Music\s*)?(?:Video|Audio|HD|4K|Visualizer|Lyric\s*Video|MV)|MV|M\/V|Audio|Lyric\s*Video|Lyrics|Visualizer|Live|Remastered|HQ|HD|Explicit|4K|1080p|Clip\s*Officiel)[\)\]]/gi, '')
    // 따옴표 및 기타 특수문자 정리
    .replace(/[【】「」]/g, '')
    .trim();

  // "Artist - Title" 또는 "Artist – Title" 패턴 분리
  const hyphenMatches = cleaned.split(/\s*[-–—|:]\s*/);
  if (hyphenMatches.length >= 2) {
    const artist = hyphenMatches[0].trim();
    const title = hyphenMatches.slice(1).join(' - ').trim();
    return {
      artist: artist || channelName || 'Unknown Artist',
      title: title || cleaned,
    };
  }

  // "Artist / Title"
  const slashMatches = cleaned.split(/\s*\/\s*/);
  if (slashMatches.length >= 2) {
    return {
      artist: slashMatches[0].trim(),
      title: slashMatches.slice(1).join(' ').trim(),
    };
  }

  return {
    artist: channelName?.replace(/ - Topic$/i, '') || 'YouTube Artist',
    title: cleaned,
  };
}

/**
 * 내 유튜브 재생목록(Playlists) 목록 조회
 */
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

/**
 * 특정 재생목록 내의 트랙(Videos) 목록 조회
 */
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

    if (!res.ok) {
      return [];
    }

    const data = await res.json();
    if (!data.items) return [];

    return data.items
      .filter((item: any) => item.snippet?.resourceId?.videoId)
      .map((item: any) => {
        const rawTitle = item.snippet?.title || 'Unknown Track';
        const channel = item.snippet?.videoOwnerChannelTitle || item.snippet?.channelTitle || '';
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

/**
 * 좋아요 표시한 동영상(Liked Videos) 중 음악 트랙 목록 조회
 */
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

    if (!res.ok) {
      return [];
    }

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

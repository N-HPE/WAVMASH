import { createClient, type SupabaseClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

// Supabase 환경변수가 없을 때 빌드/SSR 에러 방지를 위해 lazy init
let _supabase: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient {
  if (!_supabase) {
    if (!supabaseUrl || !supabaseAnonKey) {
      // 빌드 타임이나 SSR에서 환경변수 없을 때 더미 클라이언트 생성 방지
      // 런타임에서만 실제 사용됨
      return createClient('https://placeholder.supabase.co', 'placeholder-key');
    }
    _supabase = createClient(supabaseUrl, supabaseAnonKey);
  }
  return _supabase;
}

// 하위 호환을 위한 기본 export (클라이언트 컴포넌트에서만 사용)
export const supabase = typeof window !== 'undefined' && supabaseUrl
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null;

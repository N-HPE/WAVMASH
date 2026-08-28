import { redirect } from 'next/navigation';

/** 다운로드는 홈과 동일 — 메뉴 제거 후 구 URL은 홈으로 보냄 */
export default function DownloadPage() {
  redirect('/');
}

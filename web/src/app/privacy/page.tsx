import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Privacy Policy — WaveMash',
  description:
    'How WaveMash collects, uses, and stores data when you sign in with Google.',
  robots: { index: true, follow: true },
};

const SECTIONS = [
  {
    id: 'overview',
    titleKo: '개요',
    titleEn: 'Overview',
    bodyKo: (
      <>
        <p>
          WaveMash(이하 &quot;서비스&quot;)는 음악 아카이브·컬렉션·소셜 피드를 제공하는
          웹 애플리케이션입니다. 본 개인정보 처리방침은 Google 계정으로
          로그인할 때 수집·이용되는 정보에 대해 설명합니다.
        </p>
        <p>
          WaveMash is a music archive and social listening app. This Privacy
          Policy explains how we handle information when you sign in with Google.
        </p>
      </>
    ),
  },
  {
    id: 'google-data',
    titleKo: 'Google 계정에서 받는 정보',
    titleEn: 'Information from Google',
    bodyKo: (
      <>
        <p>Google Sign-In 사용 시 인증에 필요한 다음 정보만 받습니다:</p>
        <ul>
          <li>이메일 주소 (email)</li>
          <li>이름 및 프로필 사진 (제공되는 경우)</li>
          <li>Google 계정 고유 식별자</li>
        </ul>
        <p>
          When you use Google Sign-In, we receive only basic account data needed
          for authentication: email address, name and profile picture (if
          provided), and a unique Google account identifier.
        </p>
        <p className="rounded-lg border border-[#d4a853]/25 bg-[#d4a853]/8 px-3 py-2 text-white/85">
          로그인 시 Gmail, Drive, YouTube 비공개 재생목록 등 다른 Google
          서비스 데이터에는 접근하지 않습니다.
          <br />
          <span className="text-white/55">
            We do not request access to Gmail, Drive, YouTube private playlists,
            or other Google account content for login.
          </span>
        </p>
      </>
    ),
  },
  {
    id: 'use',
    titleKo: '이용 목적',
    titleEn: 'How we use data',
    bodyKo: (
      <>
        <p>수집한 정보는 다음 목적으로만 사용합니다:</p>
        <ul>
          <li>WaveMash 계정 생성 및 유지</li>
          <li>서비스 내 프로필 표시</li>
          <li>로그인 세션 인증 및 보안</li>
        </ul>
        <p>
          We use this information only to create and maintain your account,
          display your profile in the Service, and secure authentication
          sessions.
        </p>
      </>
    ),
  },
  {
    id: 'storage',
    titleKo: '저장 및 제3자 제공',
    titleEn: 'Storage and sharing',
    bodyKo: (
      <>
        <p>
          계정 정보는 서비스 운영을 위해 Supabase 데이터베이스에 저장됩니다.
          개인정보를 판매하지 않습니다. Google 사용자 데이터는 서비스 운영에
          필요한 호스팅·인프라 제공업체 또는 법령상 요구가 있는 경우를 제외하고
          제3자에게 제공하지 않습니다.
        </p>
        <p>
          Account data is stored in our Supabase database. We do not sell
          personal data. We do not share Google user data with third parties
          except as needed to operate the Service (e.g. hosting providers) or
          when required by law.
        </p>
      </>
    ),
  },
  {
    id: 'retention',
    titleKo: '보관 및 삭제',
    titleEn: 'Retention and deletion',
    bodyKo: (
      <>
        <p>
          계정이 활성인 동안 계정 정보를 보관합니다. 삭제를 원하시면 Google
          OAuth 동의 화면에 표시된 지원 이메일로 요청해 주세요.
        </p>
        <p>
          We retain account data while your account is active. To request
          deletion, contact the support email shown on the WaveMash Google
          OAuth consent screen.
        </p>
      </>
    ),
  },
  {
    id: 'contact',
    titleKo: '문의',
    titleEn: 'Contact',
    bodyKo: (
      <>
        <p>
          본 방침 또는 개인정보 관련 문의는 Google 로그인 동의 화면에 안내된
          WaveMash 개발자/지원 이메일로 연락해 주세요.
        </p>
        <p>
          For questions about this policy, use the developer / support email
          listed on the WaveMash Google sign-in consent screen.
        </p>
      </>
    ),
  },
] as const;

export default function PrivacyPage() {
  return (
    <div className="relative min-h-[calc(100vh-3.5rem)] overflow-hidden bg-[#08080f]">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          background:
            'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(212,168,83,0.18), transparent 55%), radial-gradient(ellipse 60% 40% at 100% 100%, rgba(59,130,246,0.08), transparent 50%)',
        }}
      />

      <div className="relative mx-auto max-w-3xl px-4 py-10 sm:py-14">
        <nav className="mb-8 flex items-center justify-between text-sm">
          <Link
            href="/"
            className="text-[#d4a853] transition-colors hover:text-[#e8c56a]"
          >
            ← WaveMash
          </Link>
          <a
            href="#overview"
            className="text-white/40 transition-colors hover:text-white/70"
          >
            Privacy Policy
          </a>
        </nav>

        <header className="mb-10 space-y-3 border-b border-white/10 pb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#d4a853]">
            WAVMASH
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            개인정보 처리방침
          </h1>
          <p className="text-lg text-white/50">Privacy Policy</p>
          <p className="text-sm text-white/40">Last updated: August 28, 2026</p>
          <p className="max-w-2xl text-sm leading-relaxed text-white/60">
            WaveMash는 Google 계정 로그인으로 이메일·프로필 정보만 받아
            계정을 만듭니다. 이 페이지는 Google OAuth 동의 화면에 연결되는
            공식 개인정보 처리방침입니다.
          </p>
        </header>

        <div className="mb-8 flex flex-wrap gap-2">
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              className="rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[11px] text-white/55 transition-colors hover:border-[#d4a853]/40 hover:text-[#d4a853]"
            >
              {s.titleKo}
            </a>
          ))}
        </div>

        <article className="space-y-10">
          {SECTIONS.map((s, i) => (
            <section
              key={s.id}
              id={s.id}
              className="scroll-mt-20 space-y-3 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 sm:p-6"
            >
              <h2 className="flex items-baseline gap-2 text-lg font-semibold text-white">
                <span className="tabular-nums text-[#d4a853]/80">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span>{s.titleKo}</span>
                <span className="text-sm font-normal text-white/35">
                  / {s.titleEn}
                </span>
              </h2>
              <div className="space-y-3 text-sm leading-relaxed text-white/65 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5 [&_ul]:text-white/70">
                {s.bodyKo}
              </div>
            </section>
          ))}
        </article>

        <footer className="mt-12 border-t border-white/10 pt-6 text-center text-xs text-white/35">
          <p>© {new Date().getFullYear()} WaveMash</p>
          <p className="mt-1">
            <Link href="/" className="text-[#d4a853]/80 hover:underline">
              wavmash.vercel.app
            </Link>
          </p>
        </footer>
      </div>
    </div>
  );
}

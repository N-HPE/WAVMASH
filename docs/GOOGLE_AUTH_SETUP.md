# Google 로그인 설정 (WaveMash)

WaveMash는 **Google OAuth로 로그인만** 합니다. YouTube/Spotify 계정 연동은 로그인과 분리되어 있으며, 로그인 시 **이메일·프로필** 정보만 요청합니다.

## 1. Supabase (WAVMASH 프로젝트)

1. [Supabase 대시보드](https://supabase.com/dashboard) → **WAVMASH** (`rmnlckdjplratsqhccxk`)
2. **Authentication** → **Providers** → **Google** → **Enabled**
3. Google Cloud에서 발급한 **Client ID** / **Client Secret** 입력
4. **Authentication** → **URL Configuration**
   - **Site URL**: 실제 접속 주소 (로컬: `http://localhost:3000`, 배포: Render URL)
   - **Redirect URLs**에 Site URL과 `/` 경로 포함

## 2. Google Cloud Console

### OAuth 클라이언트

1. [Google Cloud Console](https://console.cloud.google.com/) → Supabase에 연결된 프로젝트
2. **APIs & Services** → **Credentials** → OAuth 2.0 Client
3. **Authorized redirect URIs**에 반드시 포함:
   ```
   https://rmnlckdjplratsqhccxk.supabase.co/auth/v1/callback
   ```

### Google Auth platform / OAuth consent screen (중요)

메뉴 이름이 바뀌었습니다. 예전 **Scopes** 메뉴는 없고, 지금은 왼쪽 탭으로 나뉩니다.

경로 예시:
- `APIs & Services` → `OAuth consent screen`
- 또는 왼쪽에서 **Google Auth platform** → **Data Access** / **Audience**

로그인을 **누구나** 쓸 수 있게 하려면:

1. 왼쪽 **Data Access** 탭 열기
2. **Add or remove scopes** 클릭
3. YouTube 관련 스코프가 있으면 체크 해제 / 제거  
   (`youtube`, `youtube.readonly` 등)
4. 기본만 남기기: `openid`, `email`, `profile` (또는 `.../auth/userinfo.email`, `.../auth/userinfo.profile`)
5. **Update** 저장
### Publish가 회색(비활성)인 경우

Google은 External + Production 전환 전에 Branding을 이렇게 요구합니다.

- App name ✅
- User support email ✅
- **Application home page** ✅ (예: `https://wavmash.vercel.app/`)
- **Application privacy policy link** ✅ **필수** (예: `https://wavmash.vercel.app/privacy`)
- Authorized domains에 홈페이지 도메인 추가 ✅ (`wavmash.vercel.app`)
- 로고는 올리지 않는 것을 권장 (올리면 검증 필요)

앱에 `/privacy` 페이지가 있습니다. Vercel에 배포된 뒤 위 privacy URL을 Branding에 넣고 Save 하면 Audience의 **Publish app**이 활성화됩니다.

### Audience에서 Publish app 하는 방법

1. Google Cloud Console에서 프로젝트 선택
2. 왼쪽 메뉴: **Google Auth platform** → **Audience**  
   (또는 **APIs & Services** → **OAuth consent screen** → 왼쪽 **Audience**)
3. 상단에 **Publishing status**가 `Testing`으로 보일 것
4. **Publish app** 버튼 클릭
5. 확인 팝업이 뜨면 **Confirm** / 확인
6. 상태가 **In production**으로 바뀌면 완료

> email / profile / openid만 쓰는 경우, Publish만 하면 됩니다.  
> “Prepare for verification / 앱 검증 제출”은 YouTube 같은 민감 스코프를 쓸 때 필요하고, 지금 WaveMash 로그인에는 필수가 아닙니다.
> Publish 직후 첫 로그인에 “확인되지 않은 앱” 경고가 뜰 수 있습니다. Advanced → Continue로 진행하면 됩니다.

### Test users (개발 중에만)

Production 전환 전, 소수만 테스트할 때:

- **Audience** 탭 → **Test users** → 사용할 Gmail 추가

## 3. 프론트엔드 환경변수

`web/.env.local` (또는 Render 프론트엔드 env):

```env
NEXT_PUBLIC_SUPABASE_URL=https://rmnlckdjplratsqhccxk.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
```

## 4. 동작 확인

1. `npm --prefix web run dev` 실행
2. `/login` → **Google 계정으로 로그인**
3. Google 동의 화면에 **이메일·프로필**만 표시되는지 확인 (YouTube 권한 없음)
4. 로그인 후 Navbar에 프로필 아이콘이 보이면 성공

## 참고

- **다운로드** 페이지의 YouTube/Spotify URL 붙여넣기는 로그인과 무관하게 동작합니다 (서버 yt-dlp/spotdl).
- 예전에 로그인 시 YouTube 플리 연동을 요청하던 코드는 제거되었습니다.

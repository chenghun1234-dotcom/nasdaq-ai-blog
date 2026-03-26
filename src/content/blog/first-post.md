---
title: '[1단계] Astro 블로그 템플릿 선택 및 Vercel 0원 배포 가이드'
description: 'Astro Blog 템플릿으로 블로그를 만들고, GitHub 연동으로 Vercel에 무료 배포까지 한 번에 끝내는 방법'
pubDate: 'Mar 26 2026'
heroImage: '../../assets/blog-placeholder-3.jpg'
---

Astro는 마크다운(.md) 파일만 추가하면 자동으로 예쁜 블로그 글 페이지로 변환해주는, 아주 빠른 정적 사이트 생성기(SSG)입니다.
이번 단계에서는 Astro 블로그 템플릿 생성 → GitHub 업로드 → Vercel 무료 배포까지 한 번에 진행합니다.

## 1) 준비물 설치/가입

- Node.js 설치 (권장: LTS)
- GitHub 계정
- Vercel 계정 (GitHub로 로그인 권장)

설치 확인:

```bash
node -v
npm -v
git --version
```

## 2) Astro 블로그 생성

### 방법 A) 대화형(Interactive)으로 생성

터미널(또는 명령 프롬프트)을 열고 실행합니다.

```bash
npm create astro@latest
```

설치 과정에서 아래 질문이 나오면:

- How would you like to start a new project?
  - Use blog template 선택

생성 후 프로젝트 폴더로 이동합니다.

```bash
cd 프로젝트이름
```

로컬 실행(미리보기):

```bash
npm install
npm run dev
```

### 방법 B) 한 줄로 블로그 템플릿 생성(추천)

프롬프트 없이 바로 blog 템플릿으로 생성합니다.

```bash
npm create astro@latest my-blog -- --template blog
cd my-blog
npm install
npm run dev
```

## 3) GitHub 저장소에 올리기

1) GitHub에서 새 Repository 생성 (예: nasdaq-ai-blog)
2) 로컬 프로젝트에서 아래를 순서대로 실행

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/내아이디/nasdaq-ai-blog.git
git push -u origin main
```

주의:

- 내아이디는 본인 GitHub username으로 바꿔야 합니다.
- GitHub에서 Repository를 먼저 만들지 않으면 push가 실패할 수 있습니다.

## 4) Vercel에 배포하기 (자동화의 핵심)

1) https://vercel.com 접속 → GitHub로 로그인
2) 대시보드에서 Add New → Project
3) 방금 만든 GitHub 저장소(nasdaq-ai-blog) 선택 → Import
4) 설정 변경 없이 Deploy

보통 1분 내로 https://xxxx.vercel.app 형태의 무료 도메인으로 배포됩니다.

### 작동 원리(중요)

이제부터는 아래 폴더에 마크다운(.md) 글 파일만 추가하고 GitHub에 push 하면:

- Vercel이 자동으로 빌드/배포
- 블로그가 자동 업데이트

기본 Blog 템플릿 기준 글 위치:

- src/content/blog/

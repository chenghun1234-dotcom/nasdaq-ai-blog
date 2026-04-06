"""
translate_to_korean.py
영어로 작성된 3/27 ~ 4/2 블로그 포스트를 한국어로 번역 + Moomoo 블록 제거 + TradingView 한국어 CTA 추가
"""
import os
import re
import time
from google import genai
from google.genai import errors as genai_errors

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")

client = genai.Client(api_key=GEMINI_API_KEY)

# 영어 포스트 목록 (3/27 ~ 4/2)
ENGLISH_FILES = [
    # 실패한 7개 (gemini-2.5-flash 일일 한도 초과)
    "src/content/blog/2026-03-31-nke-analysis.md",
    "src/content/blog/2026-04-01-cycn-analysis.md",
    "src/content/blog/2026-04-01-psx-analysis.md",
    "src/content/blog/2026-04-01-xom-analysis.md",
    "src/content/blog/2026-04-02-sidu-analysis.md",
    "src/content/blog/2026-04-02-skyq-analysis.md",
    "src/content/blog/2026-04-02-tsla-analysis.md",
]

def get_gemini_model():
    """사용 가능한 Gemini 모델 이름 반환"""
    prefer = [
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-001",
        "models/gemini-1.5-flash",
    ]
    for name in prefer:
        try:
            # 짧은 테스트 호출
            client.models.generate_content(model=name, contents="hi")
            return name
        except genai_errors.ClientError:
            continue
    raise RuntimeError("사용 가능한 Gemini 모델이 없습니다.")

def parse_frontmatter(text):
    """YAML frontmatter 파싱"""
    match = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n(.*)', text, re.DOTALL)
    if match:
        return match.group(1), match.group(2)
    return "", text

def extract_ticker_from_filename(fname):
    """파일명에서 티커 추출 예: 2026-03-27-agx-analysis.md → AGX"""
    base = os.path.basename(fname)
    parts = base.replace('-analysis.md', '').split('-')
    # 날짜 3부분 제거: yyyy-mm-dd-TICKER
    return parts[3].upper() if len(parts) >= 4 else "UNKNOWN"

def translate_post(filepath, model_name):
    """영어 포스트를 한국어로 번역"""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    ticker = extract_ticker_from_filename(filepath)
    frontmatter, body = parse_frontmatter(content)
    
    # 기존 pubDate, heroImage 추출
    pub_date = "2026"
    for line in frontmatter.split('\n'):
        if line.startswith('pubDate:'):
            pub_date = line.replace('pubDate:', '').strip().strip('"')
            break
    
    # Moomoo 섹션 제거 (다양한 패턴)
    body = re.sub(
        r'---\s*###.*?[Mm]oomoo.*?---',
        '',
        body, flags=re.DOTALL
    )
    body = re.sub(
        r'###.*?[Mm]oomoo.*?(?=\n##|\n---|\Z)',
        '',
        body, flags=re.DOTALL
    )
    body = re.sub(
        r'\*\*\[.*?[Mm]oomoo.*?\]\(.*?\)\*\*',
        '',
        body
    )
    
    prompt = f"""You are a professional Korean financial analyst and translator.

TASK: Translate the following English stock analysis blog post to professional Korean.

RULES:
1. Keep ALL markdown formatting (##, ###, **, *, ---, etc.)
2. Keep all numbers, dollar amounts, percentages EXACTLY as-is
3. Keep ALL links and HTML exactly as-is (do NOT translate URLs, href values, or HTML attributes)
4. Keep the TradingView affiliate link and button HTML exactly as-is
5. Translate all English text to natural, professional Korean
6. Keep "TradingView" and stock ticker symbols in English
7. The tone should be professional financial analyst style in Korean
8. Do NOT add any extra commentary or preamble - output ONLY the translated markdown
9. Keep the frontmatter fields in English (title value should be translated to Korean though)

FRONTMATTER to translate (keep field names, translate values):
{frontmatter}

BODY to translate:
{body[:3000]}

Output the complete translated markdown starting with --- frontmatter ---"""

    try:
        resp = client.models.generate_content(model=model_name, contents=prompt)
        translated = resp.text.strip()
        # 코드 블록으로 감싸진 경우 제거
        if translated.startswith('```markdown'):
            translated = translated[11:]
        if translated.startswith('```'):
            translated = translated[3:]
        if translated.endswith('```'):
            translated = translated[:-3]
        translated = translated.strip()
        return translated
    except Exception as e:
        print(f"  ❌ Gemini 오류: {e}")
        return None

def main():
    print("=== 영어 포스트 한국어 번역 시작 ===\n")
    
    # 모델 선택
    print("Gemini 모델 확인 중...")
    model_name = None
    for name in ["models/gemini-2.0-flash", "models/gemini-2.0-flash-001", "models/gemini-1.5-flash"]:
        try:
            test = client.models.generate_content(model=name, contents="hi")
            if test:
                model_name = name
                print(f"  ✅ 사용 모델: {model_name}\n")
                break
        except:
            continue
    
    if not model_name:
        print("❌ 사용 가능한 Gemini 모델을 찾을 수 없습니다.")
        return
    
    success = 0
    failed = []
    
    for i, filepath in enumerate(ENGLISH_FILES, 1):
        if not os.path.exists(filepath):
            print(f"[{i:02d}/{len(ENGLISH_FILES)}] 파일 없음: {filepath}")
            failed.append(filepath)
            continue
        
        ticker = extract_ticker_from_filename(filepath)
        print(f"[{i:02d}/{len(ENGLISH_FILES)}] {ticker} 번역 중... ({os.path.basename(filepath)})")
        
        translated = translate_post(filepath, model_name)
        
        if not translated:
            print(f"  ❌ 번역 실패")
            failed.append(filepath)
            continue
        
        # 번역된 내용 저장 (BOM 없는 UTF-8)
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(translated)
        
        # 저장 확인
        with open(filepath, 'rb') as f:
            check = f.read(3)
        has_bom = check == b'\xef\xbb\xbf'
        
        # 제목 확인
        with open(filepath, 'r', encoding='utf-8') as f:
            first_lines = f.read(200)
        
        title_line = [l for l in first_lines.split('\n') if l.startswith('title:')]
        title = title_line[0] if title_line else "(제목 없음)"
        
        print(f"  ✅ 완료 (BOM: {has_bom})")
        print(f"  → {title[:80]}")
        success += 1
        
        # API 요청 간격 (Rate limit 방지)
        if i < len(ENGLISH_FILES):
            print(f"  ⏳ 8초 대기...\n")
            time.sleep(8)
    
    print(f"\n=== 번역 완료 ===")
    print(f"성공: {success}/{len(ENGLISH_FILES)}")
    if failed:
        print(f"실패: {len(failed)}개")
        for f in failed:
            print(f"  - {f}")

if __name__ == "__main__":
    main()

import subprocess

# 원본 커밋 해시 (heroImage 수정 이전 - 깨끗한 한국어 UTF-8)
originals = {
    'amd':  '508d54e',
    'dkng': '89dc557',
    'kod':  'd83a6f8',
    'meta': '80c2fbb',
    'rddt': 'e2f50c8',
    'ugro': 'e8c3dcc',
}

print("=== 3/26 한국어 포스트 복원 ===\n")

for ticker, commit in originals.items():
    fname = f'src/content/blog/2026-03-26-{ticker}-analysis.md'
    
    # git에서 원본 바이너리 그대로 가져오기 (PowerShell 인코딩 우회)
    result = subprocess.run(
        ['git', 'show', f'{commit}:{fname}'],
        capture_output=True
    )
    
    if result.returncode != 0:
        print(f'ERROR: {ticker} - {result.stderr.decode("utf-8", errors="replace")}')
        continue
    
    raw = result.stdout
    
    # UTF-8 디코딩 검증
    try:
        text = raw.decode('utf-8')
        print(f'{ticker}: UTF-8 OK ({len(text)} chars)')
    except UnicodeDecodeError as e:
        print(f'{ticker}: UTF-8 decode failed: {e}')
        continue
    
    # heroImage 경로 수정 (절대 → 상대)
    old_path = 'heroImage: "/blog-placeholder-about.jpg"'
    new_path = 'heroImage: "../../assets/blog-placeholder-about.jpg"'
    if old_path in text:
        text = text.replace(old_path, new_path)
        print(f'  → heroImage 경로 수정됨')
    else:
        print(f'  → heroImage 경로 이미 올바름')
    
    # BOM 없이 UTF-8로 저장 (LF 줄바꿈)
    with open(fname, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    
    # 저장 확인
    with open(fname, 'rb') as f:
        check = f.read(100)
    has_bom = check[:3] == b'\xef\xbb\xbf'
    print(f'  → 저장 완료 (BOM: {has_bom})')
    print(f'  → 제목: {[l for l in text.split(chr(10)) if l.startswith("title:")][0]}')
    print()

print("=== 복원 완료 ===")

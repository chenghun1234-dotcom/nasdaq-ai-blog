import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from google import genai
from google.genai import errors as genai_errors
from github import Github
from github.GithubException import GithubException

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_NAME = os.environ.get("REPO_NAME", "chenghun1234-dotcom/nasdaq-ai-blog")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "models/gemini-2.5-flash")
KST = ZoneInfo("Asia/Seoul")


def now_kst() -> datetime:
    return datetime.now(KST)

def get_trending_tickers(limit: int = 3) -> list:
    """야후 파이낸스 API를 호출하여 오늘 가장 핫한 주식 심볼 추출"""
    print("🔥 오늘의 미국 증시 트렌딩 종목을 탐색합니다...")
    url = "https://query1.finance.yahoo.com/v1/finance/trending/US"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        quotes = data['finance']['result'][0]['quotes']
        
        tickers = []
        for quote in quotes:
            symbol = quote['symbol']
            # 순수 영문 알파벳으로만 이루어진 '개별 주식'만 필터링
            if symbol.isalpha() and len(symbol) <= 5:
                tickers.append(symbol)
            if len(tickers) == limit:
                break
                
        print(f"🎯 오늘의 타겟 종목이 선정되었습니다: {tickers}")
        return tickers if tickers else ["NVDA", "TSLA", "MSFT"]
    except Exception as e:
        print(f"❌ 트렌딩 종목 수집 실패: {e}")
        return ["NVDA", "TSLA", "MSFT"]

def fetch_stock_data(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    info = getattr(stock, "info", {}) or {}
    return {
        "name": info.get("shortName", ticker),
        "price": info.get("currentPrice", "N/A"),
        "previous_close": info.get("previousClose", "N/A"),
        "pe_ratio": info.get("trailingPE", "N/A"),
        "market_cap": info.get("marketCap", "N/A"),
        "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
        "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
    }

def generate_stock_chart(ticker: str, date_str: str) -> str | None:
    """최근 1달 주가 데이터를 가져와 차트 이미지로 저장"""
    print(f"📊 [{ticker}] 주가 차트 생성 중...")
    
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1mo")
    
    if hist.empty:
        print("데이터가 없어 차트를 그릴 수 없습니다.")
        return None
        
    plt.figure(figsize=(10, 5))
    plt.plot(hist.index, hist['Close'], color='#2563eb', linewidth=2, marker='o', markersize=4)
    
    plt.title(f"{ticker} - Recent 1 Month Price Trend", fontsize=16, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Closing Price (USD)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.gcf().autofmt_xdate()
    
    file_name = f"{ticker.lower()}_{date_str}.png"
    plt.savefig(file_name, bbox_inches='tight', dpi=150)
    plt.close()
    
    return file_name

def upload_image_to_github(repo, local_file_path: str, ticker: str) -> str | None:
    """생성된 차트 이미지를 GitHub의 public 폴더에 업로드"""
    print(f"🖼️ [{ticker}] 차트 이미지를 GitHub에 업로드 중...")
    
    github_image_path = f"public/images/{local_file_path}"
    
    try:
        with open(local_file_path, "rb") as file:
            content = file.read()
            
        repo.create_file(github_image_path, f"Add chart image for {ticker}", content, branch="main")
        print("✅ 이미지 업로드 완료!")
        
        os.remove(local_file_path)
        
        return f"/images/{local_file_path}"
        
    except GithubException as e:
        if e.status == 422: # 이미 존재하는 경우 덮어쓰기
            try:
                existing = repo.get_contents(github_image_path, ref="main")
                with open(local_file_path, "rb") as file:
                    content = file.read()
                repo.update_file(
                    path=github_image_path,
                    message=f"Update chart image for {ticker}",
                    content=content,
                    sha=existing.sha,
                    branch="main"
                )
                print("✅ 이미지 업데이트 완료!")
                os.remove(local_file_path)
                return f"/images/{local_file_path}"
            except Exception as inner_e:
                print(f"❌ 이미지 업데이트 실패: {inner_e}")
                return None
        print(f"❌ 이미지 업로드 실패: {e}")
        return None
    except Exception as e:
        print(f"❌ 이미지 업로드 실패: {e}")
        return None

def generate_blog_post(data: dict, ticker: str, image_path: str = "") -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")
    client = genai.Client(api_key=GEMINI_API_KEY)
    current_time = now_kst()
    today_str = current_time.strftime("%Y-%m-%d")
    
    prompt = f"""
    당신은 월스트리트의 전문 금융 애널리스트입니다.
    제공된 데이터를 바탕으로 한국 개인 투자자들이 읽기 쉽고 전문적인 블로그 포스트를 **한국어**로 작성해 주세요.
    
    [Data]
    - 종목명: {data['name']} ({ticker})
    - 현재가: ${data['price']}
    - 전일 종가: ${data['previous_close']}
    - PER: {data['pe_ratio']}
    - 52 Week High: ${data['52_week_high']}
    - 52 Week Low: ${data['52_week_low']}

    [Rules]
    1. 마크다운(.md) 형식으로 작성하세요.
    2. 글의 맨 처음에 아래의 YAML Frontmatter를 정확히 포함하세요:
    ---
    title: "{data['name']} ({ticker}) 주가 전망 및 심층 분석 - {today_str}"
    description: "현재가, PER, 최근 트렌드를 바탕으로 한 {data['name']} ({ticker})의 심층 분석 리포트입니다."
    pubDate: "{today_str}"
    heroImage: "../../assets/blog-placeholder-about.jpg"
    ---

    3. 분석 섹션(본문) 시작 부분에 아래 차트 이미지 태그를 정확히 삽입하세요:
       ![{ticker} 주가 차트]({image_path})
       
       차트 이미지 바로 아래에 트레이딩뷰 제휴 버튼 HTML 코드를 반드시 삽입하세요 (코드 수정 금지):
       
       <div style="text-align: center; margin: 20px 0;">
         <a href="https://www.tradingview.com/?aff_id=165077&aff_sub=under_chart&source=blog" target="_blank" style="display:inline-block; background-color:#131722; color:white; padding:10px 20px; font-weight:bold; border-radius:6px; text-decoration:none; font-size: 0.95rem;">
           📊 트레이딩뷰에서 {ticker} 차트 심층 분석하기 (무료 체험)
         </a>
       </div>

    4. H2 (##) 및 H3 (###) 태그를 사용하여 서론, 기술적 분석, 결론 등을 나누어 가독성을 높이세요.

    5. 결론 파트 직후에 독자의 클릭을 유도하는 아래 마크다운 블록을 정확히 삽입하세요 (문구와 링크 수정 금지):

    ---
    ### 📊 {ticker}의 실시간 차트와 정밀 분석이 더 필요하신가요?
    전문 투자자들이 입을 모아 추천하는 **트레이딩뷰(TradingView)**를 활용해 보세요. 
    오늘 분석한 {ticker}의 주가 흐름을 월가 애널리스트들과 동일한 환경에서 실시간으로 추적할 수 있습니다. 
    
    지금 아래 링크를 통해 가입하시면 **모든 프리미엄 기능을 30일 동안 무료**로 체험해 보실 수 있습니다.
    
    👉 **[트레이딩뷰 프리미엄 혜택 받고 실시간 차트 보기](https://www.tradingview.com/?aff_id=165077&aff_sub=under_chart&source=blog)**
    
    *※ 더 정확한 데이터가 더 나은 수익을 만듭니다.*
    ---

    6. 한국 투자자들이 공감할 수 있도록 전문적이고 객관적인 톤을 유지하며, 데이터에 없는 내용을 지어내지(Hallucination) 마세요.
    """
    try:
        name = GEMINI_MODEL
        if not name.startswith("models/"):
            name = f"models/{name}"
        resp = client.models.generate_content(model=name, contents=prompt)
    except genai_errors.ClientError:
        try_names = [
            "models/gemini-2.5-flash",
            "models/gemini-2.0-flash",
            "models/gemini-2.0-flash-001",
            "models/gemini-2.5-pro",
        ]
        for name in try_names:
            try:
                resp = client.models.generate_content(model=name, contents=prompt)
                break
            except genai_errors.ClientError:
                resp = None
        if not resp:
            models = list(client.models.list())
            names = [getattr(m, "name", "") for m in models]
            prefer = [n for n in names if "gemini-2.5" in n and "flash" in n]
            if not prefer:
                prefer = [n for n in names if "gemini-2.0" in n and "flash" in n]
            if not prefer:
                prefer = [n for n in names if "gemini-2.5" in n and "pro" in n]
            if not prefer and names:
                prefer = names
            if not prefer:
                raise
            ok = None
            for name in prefer:
                try:
                    ok = client.models.generate_content(model=name, contents=prompt)
                    resp = ok
                    break
                except genai_errors.ClientError:
                    continue
            if not resp:
                raise
    return resp.text or ""

def upload_to_github(markdown_content: str, ticker: str) -> None:
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN is not set")
    if not REPO_NAME:
        raise RuntimeError("REPO_NAME is not set")
    try:
        from github import Auth

        g = Github(auth=Auth.Token(GITHUB_TOKEN))
    except Exception:
        g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    today_str = now_kst().strftime("%Y-%m-%d")
    file_path = f"src/content/blog/{today_str}-{ticker.lower()}-analysis.md"
    commit_message = f"Auto Post: {ticker} 주가 분석 업데이트"
    try:
        repo.create_file(path=file_path, message=commit_message, content=markdown_content, branch="main")
    except GithubException as e:
        if e.status == 422:
            existing = repo.get_contents(file_path, ref="main")
            repo.update_file(
                path=file_path,
                message=commit_message,
                content=markdown_content,
                sha=existing.sha,
                branch="main",
            )
            return
        raise

def main():
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN is not set")
        return
    try:
        from github import Auth
        g = Github(auth=Auth.Token(GITHUB_TOKEN))
    except Exception:
        g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    current_time = now_kst()
    today_str = current_time.strftime("%Y-%m-%d")
    print(f"🕒 한국 시간 기준 자동 포스팅 날짜: {today_str} ({current_time.isoformat()})")

    dynamic_tickers = get_trending_tickers(limit=3)
    print(f"\n총 {len(dynamic_tickers)}개 핫이슈 종목 포스팅 자동화를 시작합니다.")
    
    for ticker in dynamic_tickers:
        print(f"\n▶ [{ticker}] 작업 시작...")
        try:
            # 1. 주가 데이터 수집
            data = fetch_stock_data(ticker)
            
            # 2. 📈 차트 그리기 및 이미지 임시 저장
            local_image_name = generate_stock_chart(ticker, today_str)
            
            md_image_path = ""
            if local_image_name:
                # 3. 🖼️ 이미지를 GitHub public/images 폴더에 업로드
                md_image_path = upload_image_to_github(repo, local_image_name, ticker) or ""
            
            # 4. ✍️ AI 글 작성 (이때 이미지 경로를 프롬프트에 전달)
            content = generate_blog_post(data, ticker, md_image_path)
            if not content.strip():
                raise RuntimeError("Empty content returned from Gemini")
                
            # 5. 🚀 완성된 마크다운 글을 GitHub src/content/blog 폴더에 업로드
            upload_to_github(content, ticker)
            print(f"✅ [{ticker}] GitHub 업로드 성공!")
            
            # 마지막 종목이 아니면 45초 대기 (API 속도 제한 방지)
            if ticker != dynamic_tickers[-1]:
                print("다음 종목 처리를 위해 45초 대기합니다...")
                time.sleep(45)
        except Exception as e:
            print(f"❌ [{ticker}] 처리 중 오류 발생: {e}")
            continue

    print("\n🎉 오늘의 트렌딩 포스팅 작업이 완벽하게 완료되었습니다!")

if __name__ == "__main__":
    main()


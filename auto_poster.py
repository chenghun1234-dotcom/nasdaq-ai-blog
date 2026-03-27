import os
import time
from datetime import datetime
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
    today_title = datetime.now().strftime("%Y-%m-%d")
    today_pub = datetime.now().strftime("%b %d %Y")
    
    image_markdown = f"\n![{ticker} Stock Chart]({image_path})\n" if image_path else ""
    
    prompt = f"""
    You are a professional Wall Street financial analyst.
    Based on the provided data, write an engaging and professional blog post in **English**.
    
    [Data]
    - Name: {data['name']} ({ticker})
    - Current Price: ${data['price']}
    - Previous Close: ${data['previous_close']}
    - P/E Ratio: {data['pe_ratio']}
    - 52 Week High: ${data['52_week_high']}
    - 52 Week Low: ${data['52_week_low']}

    [Rules]
    1. Write in Markdown (.md) format.
    2. Include the following YAML Frontmatter at the very beginning exactly as shown:
    ---
    title: "{data['name']} ({ticker}) Stock Analysis & Price Target - {today_title}"
    description: "In-depth analysis of {data['name']} ({ticker}) based on current price, P/E ratio, and recent trends."
    pubDate: "{today_pub}"
    heroImage: "../../assets/blog-placeholder-about.jpg"
    ---
    3. Insert this exact markdown image tag at the beginning of the analysis section:
       ![{ticker} Stock Chart]({image_path})
    4. Use H2 (##) and H3 (###) tags for Introduction, Technical Analysis, and Conclusion.
    5. Keep the tone professional, objective, and easy to read for retail investors. Do not hallucinate data.
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
    today_str = datetime.now().strftime("%Y-%m-%d")
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
    today_str = datetime.now().strftime("%Y-%m-%d")

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


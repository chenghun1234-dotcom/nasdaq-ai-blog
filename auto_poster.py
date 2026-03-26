import os
from datetime import datetime
import yfinance as yf
from google import genai
from google.genai import errors as genai_errors
from github import Github
from github.GithubException import GithubException

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_NAME = os.environ.get("REPO_NAME", "chenghun1234-dotcom/nasdaq-ai-blog")
TARGET_TICKER = os.environ.get("TARGET_TICKER", "NVDA")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "models/gemini-2.5-flash")

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

def generate_blog_post(data: dict, ticker: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")
    client = genai.Client(api_key=GEMINI_API_KEY)
    today_title = datetime.now().strftime("%Y-%m-%d")
    today_pub = datetime.now().strftime("%b %d %Y")
    prompt = f"""
너는 미국 나스닥 주식을 전문적으로 분석하는 한국인 투자 전문가야.
다음 제공된 데이터를 바탕으로 투자자들이 흥미로워할 블로그 포스팅을 작성해줘.

[데이터]
- 종목명: {data['name']} ({ticker})
- 현재가: ${data['price']}
- 전일종가: ${data['previous_close']}
- PER: {data['pe_ratio']}
- 52주 최고가: ${data['52_week_high']}
- 52주 최저가: ${data['52_week_low']}

[작성 규칙]
1. 마크다운(.md) 형식으로 작성할 것.
2. Astro 블로그가 인식할 수 있도록 글의 가장 첫 부분에 반드시 아래와 같은 YAML Frontmatter를 포함할 것:
---
title: "{data['name']} ({ticker}) 주가 분석 및 전망 - {today_title}"
description: "나스닥 {data['name']}의 현재가, PER, 52주 최고/최저가 데이터를 바탕으로 한 상세 분석 리포트입니다."
pubDate: "{today_pub}"
heroImage: "../../assets/blog-placeholder-about.jpg"
---
3. H2(##), H3(###) 태그를 사용하여 서론, 본론(데이터 분석), 결론(투자 인사이트) 구조로 가독성 있게 작성할 것.
4. 친절하고 전문적인 블로거의 말투를 사용할 것.
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

if __name__ == "__main__":
    data = fetch_stock_data(TARGET_TICKER)
    content = generate_blog_post(data, TARGET_TICKER)
    if not content.strip():
        raise RuntimeError("Empty content returned from Gemini")
    upload_to_github(content, TARGET_TICKER)


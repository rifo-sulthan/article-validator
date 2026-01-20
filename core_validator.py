# core_validator.py
import requests
from bs4 import BeautifulSoup
import re
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import random
import cloudscraper
import asyncio
from playwright.async_api import async_playwright
# Changed import to point to the renamed wrapper
from classifier_wrapper import GenericZeroShotClassifier

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

class ArticleValidator:
    def __init__(self, model_path, device=-1):
        self.classifier = GenericZeroShotClassifier(model_path, device)
        self.timeout = 25
        self.max_retries = 2

    def create_enhanced_session(self):
        session = requests.Session()
        retry = Retry(total=self.max_retries, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def get_headers(self):
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
        }

    def fetch_playwright_sync(self, url):
        try:
            return asyncio.run(self._fetch_playwright(url))
        except Exception as e:
            return None, f"Playwright error: {e}"

    async def _fetch_playwright(self, url):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
                context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
                await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                page = await context.new_page()
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                    content = await page.content()
                    if any(x in content.lower() for x in ['access denied', 'cloudflare', 'captcha']):
                        await browser.close()
                        return None, "Blocked (Playwright)"
                    await browser.close()
                    return content, "Success (Playwright)"
                except Exception as e:
                    await browser.close()
                    return None, f"Nav error: {e}"
        except Exception as e:
            return None, f"Setup error: {e}"

    def smart_fetch(self, url):
        methods = []
        # 1. Requests
        try:
            resp = self.create_enhanced_session().get(url, timeout=self.timeout, headers=self.get_headers())
            if resp.status_code == 200: return resp.text, "Requests"
            methods.append(f"Req:{resp.status_code}")
        except Exception as e: methods.append(f"Req:{e}")

        # 2. Cloudscraper
        try:
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(url, timeout=self.timeout)
            if resp.status_code == 200: return resp.text, f"Cloudscraper | {methods[-1]}"
            methods.append(f"CS:{resp.status_code}")
        except Exception as e: methods.append(f"CS:{e}")

        # 3. Playwright
        html, msg = self.fetch_playwright_sync(url)
        if html: return html, f"Playwright | {methods[-1]}"
        
        return None, " | ".join(methods)

    def is_article(self, soup):
        if soup.find("article") or soup.find("meta", property="og:type", content="article"): return True
        return len(soup.get_text(strip=True).split()) > 300

    def validate_url(self, url, candidate_labels, positive_labels, threshold=0.60):
        """
        Validate a single URL against labels.
        Returns: (status, top_label, score, list_label_scores, note)
        """
        html, method = self.smart_fetch(url)
        if not html:
            return "No", "None", 0, {}, f"Fetch Failed: {method}"

        try:
            soup = BeautifulSoup(html, "html.parser")
            for s in soup(["script", "style"]): s.decompose()
            
            if not self.is_article(soup):
                return "No", "Not Article", 0, {}, method
            
            text = soup.get_text(separator=" ", strip=True)
            if len(text.split()) < 50:
                return "No", "Too Short", 0, {}, method
            
            # Classify
            result = self.classifier.classify_article(text, candidate_labels, threshold=threshold, multi_label=True)
            all_scores = result["all_scores"]
            
            # Logic: Check if ANY positive label > threshold
            is_relevant = False
            top_pos_score = 0
            best_label = result["top_label"] # Default to whatever machine thinks is top
            
            for label in positive_labels:
                score = all_scores.get(label, 0)
                if score >= threshold:
                    is_relevant = True
                    if score > top_pos_score:
                        top_pos_score = score
                        best_label = label
            
            status = "Yes" if is_relevant else "No"
            final_score = top_pos_score if is_relevant else result["top_score"]
            note = f"Label: {best_label} ({final_score:.2f}) | {method}"
            
            return status, best_label, final_score, all_scores, note
            
        except Exception as e:
            return "No", "Error", 0, {}, f"Err: {e}"

    def prefilter_metadata(self, title, url, candidate_labels, positive_labels, threshold_valid=0.85, threshold_invalid=0.30, force_valid_keywords=None):
        """
        Validate based on Title and URL only.
        Returns: (status, best_label, score, note)
        Status: 'Valid', 'Not Valid', 'Not Sure'
        """
        # Combine text
        text = f"{title} {url}"
        
        # 0. Check Keyword Overrides (Score Boost)
        keyword_boost = 0.0
        matched_keywords = []
        if force_valid_keywords:
            text_lower = text.lower()
            for kw in force_valid_keywords:
                if kw.lower() in text_lower:
                    keyword_boost += 0.3
                    matched_keywords.append(kw)
        
        # Classify (using multi_label=True to get independent scores)
        # We pass threshold=0 because we want to see the score regardless 
        result = self.classifier.classify_article(text, candidate_labels, threshold=0.0, multi_label=True)
        all_scores = result["all_scores"]
        
        # Find the highest score among positive labels
        top_pos_score = 0
        best_label = "None"
        
        for label in positive_labels:
            score = all_scores.get(label, 0)
            if score > top_pos_score:
                top_pos_score = score
                best_label = label
        
        # If no positive label had a score > 0 (unlikely if model works), pick top overall
        if top_pos_score == 0:
             best_label = result["top_label"]
             # If top label is not positive, score is effectively 0 for relevance
        
        # Apply Boost
        original_score = top_pos_score
        top_pos_score = min(1.0, top_pos_score + keyword_boost)
        
        # Determine Status
        if top_pos_score >= threshold_valid:
            status = "Valid"
        elif top_pos_score <= threshold_invalid:
            status = "Not Valid"
        else:
            status = "Not Sure"
            
        note = f"Meta-Label: {best_label} ({top_pos_score:.2f})"
        if matched_keywords:
            note += f" | Boosted +{keyword_boost:.1f} by {matched_keywords}"
        
        return status, best_label, top_pos_score, note

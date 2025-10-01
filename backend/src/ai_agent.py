# AI Agent for analyzing scraped flood data using Ollama
import json
import time
import requests
from typing import List, Dict, Any
import re

class FloodAnalysisAgent:
    def __init__(self, ollama_url: str = "http://localhost:11434", model_name: str = "gpt-oss:20b", timeout: int = 120):
        self.ollama_url = ollama_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        
        # Lebanese-specific flood keywords (Arabic + English)
        self.lebanese_keywords = [
            # Water bodies and coastal terms (Arabic)
            'شاطئ', 'شط', 'بحر', 'موج', 'ساحل', 'منسوب البحر', 'مد بحري', 'تسونامي', 'أمواج',
            
            # Water bodies and coastal terms (English)
            'beach', 'shore', 'sea', 'waves', 'coast', 'coastal', 'sea level', 'tide', 'tsunami', 'mediterranean',
            
            # Flood and rain terms (Arabic)
            'فيضان', 'الفيضان', 'فيضانات', 'سيل', 'سيول', 'نهر', 'مجرى', 'مصب',
            'امطار', 'الامطار', 'غزيرة', 'الغزيرة', 'غزارة', 'تغرق', 'غرق',
            
            # Flood and rain terms (English)
            'flood', 'flooding', 'flooded', 'floods', 'torrent', 'stream', 'river', 'waterway', 'outlet',
            'rain', 'rainfall', 'heavy rain', 'downpour', 'precipitation', 'drench', 'drown', 'drowning',
            
            # Lebanese rivers (Arabic)
            'نهر ابراهيم', 'نهر الكلب', 'نهر الدامور', 'نهر اسطوان', 'نهر الاسطوان', 
            'نهر الكبير', 'النهر الكبير', 'نهر الجوز', 'نهر الليطاني', 'الليطاني', 
            'نهر عرقا', 'نهر بيروت', 'نهر الحاصباني', 'نهر الوزاني', 'نهر رشعين', 
            'نهر الغدير', 'نهرالخردلي', 'نهر الأولي', 'نهر بسري', 'نهر سينيق', 
            'نهر أبو الأسود', 'نهر الزهراني', 'نهر البارد', 'نهر أبو علي', 'نهر الفيدار', 
            'نهر المدفون', 'نهر وادي برسا', 'نهر العصفور', 'نهر العاصي', 'نهر العويك', 'نهر القاسمية',
            
            # Lebanese rivers (English)
            'Ibrahim River', 'Nahr Ibrahim', 'Dog River', 'Nahr el Kalb', 'Damour River', 'Nahr Damour',
            'Istuwan River', 'Kabir River', 'Jouz River', 'Litani River', 'Nahr Litani',
            'Arqa River', 'Beirut River', 'Nahr Beirut', 'Hasbani River', 'Wazzani River', 
            'Racheine River', 'Ghadir River', 'Khardali River', 'Awali River', 'Bisri River',
            'Siniaq River', 'Abu Aswad River', 'Zahrani River', 'Barid River', 'Abu Ali River',
            'Fidar River', 'Madfoun River', 'Wadi Bersa River', 'Asfour River', 'Orontes River', 'Asi River',
            'Aweik River', 'Qasimiye River',
            
            # Regional rivers (Arabic + English)
            'النهر الجنوبي', 'النهر الشمالي', 'Southern River', 'Northern River',
            
            # Lebanese locations prone to flooding (Arabic)
            'الغزيل', 'البردوني', 'يحفوفا', 'القاع', 'الفاكهة', 'اللبوة', 'عرسال', 
            'راس بعلبك', 'رأس بعلبك', 'وادي', 'وادي نحلة', 'النبي عثمان', 'سهل',
            
            # Lebanese locations prone to flooding (English)
            'Ghazil', 'Bardouni', 'Yahfoufa', 'Qaa', 'Fakiha', 'Labweh', 'Arsal',
            'Ras Baalbek', 'wadi', 'Wadi Nahla', 'Nabi Othman', 'plain', 'valley',
            
            # Lebanese cities/regions (English)
            'Beirut', 'Tripoli', 'Sidon', 'Tyre', 'Baalbek', 'Zahle', 'Jounieh', 'Byblos',
            'Akkar', 'Bekaa', 'Mount Lebanon', 'South Lebanon', 'North Lebanon',
            
            # Weather and storm terms (Arabic + English)
            'عاصفة', 'رياح', 'اعصار', 'منخفض جوي', 'storm', 'wind', 'cyclone', 'low pressure',
            
            # Arabic months (for seasonal analysis)
            'كانون الثاني', 'شباط', 'آذار', 'نيسان', 'أيار', 'حزيران', 
            'تموز', 'آب', 'أيلول', 'تشرين الأول', 'تشرين الثاني', 'كانون الأول',
            
            # English months
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        
        # Combined keywords for comprehensive detection
        self.all_keywords = self.lebanese_keywords
    
    def check_keywords_presence(self, title: str, content: str) -> Dict[str, Any]:
        """
        Check for presence of Lebanese and flood keywords in the text
        Returns immediate flag if keywords are found
        """
        combined_text = f"{title} {content}".lower()
        
        found_keywords = []
        found_lebanese = []
        
        # Check all keywords
        for keyword in self.all_keywords:
            if keyword.lower() in combined_text:
                found_keywords.append(keyword)
                # Check if it's Arabic (Lebanese specific)
                if any(ord(char) > 127 for char in keyword):  # Contains non-ASCII (Arabic)
                    found_lebanese.append(keyword)
        
        # Determine relevance based on keywords
        total_found = len(found_keywords)
        has_lebanese = len(found_lebanese) > 0
        
        # High relevance if Lebanese keywords are found
        if has_lebanese:
            confidence = min(95, 70 + (len(found_lebanese) * 5))
            category = "lebanese_flood_content"
        elif total_found >= 3:
            confidence = min(90, 60 + (total_found * 5))
            category = "flood_news"
        elif total_found >= 1:
            confidence = 40 + (total_found * 10)
            category = "possible_flood_content"
        else:
            confidence = 10
            category = "not_flood_related"
        
        return {
            "is_relevant": total_found > 0,
            "confidence": confidence,
            "keywords_found": found_keywords,
            "lebanese_keywords_found": found_lebanese,
            "category": category,
            "keyword_match_count": total_found,
            "priority_flag": has_lebanese  # High priority if Lebanese keywords found
        }
    
    def is_flood_related(self, title: str, content: str) -> Dict[str, Any]:
        """
        Analyze if an article is flood-related using keywords first, then AI analysis
        Returns relevance score and reasoning
        """
        # First check for keywords (fast)
        keyword_result = self.check_keywords_presence(title, content)
        
        # If high-priority keywords found (Lebanese), return immediately
        if keyword_result.get("priority_flag", False):
            return {
                "is_relevant": True,
                "confidence": keyword_result["confidence"],
                "keywords_found": keyword_result["keywords_found"],
                "lebanese_keywords_found": keyword_result["lebanese_keywords_found"],
                "summary": f"Contains Lebanese flood-related keywords: {', '.join(keyword_result['lebanese_keywords_found'][:3])}",
                "category": keyword_result["category"],
                "analysis_method": "keyword_priority"
            }
        
        # If some keywords found, enhance confidence but still use AI
        if keyword_result["is_relevant"]:
            try:
                ai_result = self._ai_analysis(title, content)
                # Combine keyword and AI analysis
                combined_confidence = min(95, (keyword_result["confidence"] + ai_result.get("confidence", 50)) / 2 + 10)
                
                return {
                    "is_relevant": ai_result.get("is_relevant", True),
                    "confidence": int(combined_confidence),
                    "keywords_found": keyword_result["keywords_found"],
                    "lebanese_keywords_found": keyword_result.get("lebanese_keywords_found", []),
                    "summary": ai_result.get("summary", "Flood-related content detected"),
                    "category": ai_result.get("category", keyword_result["category"]),
                    "analysis_method": "keyword_plus_ai"
                }
            except Exception as e:
                # Fallback to keyword analysis if AI fails
                return {
                    "is_relevant": True,
                    "confidence": keyword_result["confidence"],
                    "keywords_found": keyword_result["keywords_found"],
                    "lebanese_keywords_found": keyword_result.get("lebanese_keywords_found", []),
                    "summary": "Flagged by keyword detection (AI unavailable)",
                    "category": keyword_result["category"],
                    "analysis_method": "keyword_fallback",
                    "ai_error": str(e)
                }
        
        # No keywords found, try AI analysis
        try:
            return self._ai_analysis(title, content)
        except Exception as e:
            return {
                "is_relevant": False,
                "confidence": 0,
                "keywords_found": [],
                "lebanese_keywords_found": [],
                "summary": f"No flood keywords detected. AI analysis failed: {str(e)}",
                "category": "not_flood_related",
                "analysis_method": "no_detection",
                "error": str(e)
            }
    
    def _ai_analysis(self, title: str, content: str) -> Dict[str, Any]:
        """
        Perform AI analysis using Ollama
        """
        prompt = f"""
        Analyze this article and determine if it's related to floods, flooding, or flood disasters.
        Pay special attention to Arabic text and Lebanese locations.
        
        Title: {title[:200]}
        Content: {content[:1000]}...
        
        Please respond with a JSON object containing:
        - "is_relevant": true/false
        - "confidence": 0-100 (percentage confidence)
        - "keywords_found": list of flood-related keywords found
        - "summary": brief 1-2 sentence summary
        - "category": one of ["flood_news", "flood_preparedness", "flood_research", "flood_policy", "lebanese_flood_content", "not_flood_related"]
        
        Only respond with valid JSON, no other text.
        """.strip()
        
        response = self._call_ollama(prompt)
        result = self._parse_ai_response(response)
        result["analysis_method"] = "ai_only"
        return result
    
    def analyze_article(self, title: str, content: str) -> Dict[str, Any]:
        """
        Main method to analyze an article with both keyword detection and AI analysis
        """
        # Check if flood-related
        relevance_analysis = self.is_flood_related(title, content)
        
        # If relevant, extract detailed info
        detailed_info = {}
        if relevance_analysis.get("is_relevant", False):
            detailed_info = self.extract_key_info(title, content)
        
        return {
            "relevance_analysis": relevance_analysis,
            "detailed_info": detailed_info,
            "analyzed_at": str(time.time())
        }
    
    def extract_key_info(self, title: str, content: str) -> Dict[str, Any]:
        """
        Extract key information from flood-related articles
        """
        prompt = f"""
        Extract key information from this flood-related article:
        
        Title: {title}
        Content: {content[:2000]}...
        
        Please respond with a JSON object containing:
        - "location": locations mentioned (cities, states, countries)
        - "date_mentioned": any dates mentioned in the article
        - "flood_type": type of flooding (river, flash, coastal, urban, etc.)
        - "severity": severity level (minor, moderate, major, catastrophic, unknown)
        - "casualties": any casualties mentioned (numbers or "none mentioned")
        - "damage": damage information mentioned
        - "key_facts": list of 3-5 most important facts
        
        Only respond with valid JSON, no other text.
        """.strip()

        response = self._call_ollama(prompt)
        return self._parse_ai_response(response)

    def _call_ollama(self, prompt: str, num_predict: int = 512, temperature: float = 0.2) -> str:
        """
        Call Ollama. Prefer /api/generate; if unavailable or empty, try /api/chat.
        Retry once with relaxed params. Return raw text (may be non-JSON).
        """
        base = self.ollama_url.rstrip("/")

        def _extract_chat_text(jd: Dict[str, Any]) -> str:
            if not isinstance(jd, dict):
                return ""
            # Standard chat response
            msg = jd.get("message")
            if isinstance(msg, dict) and msg.get("content"):
                return str(msg["content"]).strip()
            # Some variants return 'messages'
            msgs = jd.get("messages")
            if isinstance(msgs, list):
                parts = [m.get("content", "") for m in msgs if isinstance(m, dict) and m.get("content")]
                txt = "\n".join([p for p in parts if p]).strip()
                if txt:
                    return txt
            # Some builds still use 'response'
            if jd.get("response"):
                return str(jd["response"]).strip()
            return ""

        def _try_generate(np: int, temp: float) -> str:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": np, "temperature": temp},
            }
            r = requests.post(f"{base}/api/generate", json=payload, timeout=self.timeout)
            if r.status_code in (404, 405):
                raise requests.HTTPError(f"/api/generate {r.status_code}", response=r)
            r.raise_for_status()
            data = r.json()
            return (data.get("response") or "").strip()

        def _try_chat(np: int, temp: float) -> str:
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant for flood OSINT and Google search query generation."},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {"num_predict": np, "temperature": temp},
            }
            rc = requests.post(f"{base}/api/chat", json=payload, timeout=self.timeout)
            rc.raise_for_status()
            return _extract_chat_text(rc.json())

        # First attempt: /api/generate
        try:
            txt = _try_generate(num_predict, temperature)
            if txt:
                return txt
        except requests.HTTPError as e:
            # If 404/405 we'll try chat next; for other errors, attempt chat fallback instead of raising
            if not (getattr(e, "response", None) and e.response.status_code in (404, 405)):
                try:
                    txt = _try_chat(num_predict, max(0.1, temperature))
                    if txt:
                        return txt
                except Exception:
                    pass

        # Fallback: /api/chat
        try:
            txt = _try_chat(num_predict, max(0.1, temperature))
            if txt:
                return txt
        except Exception:
            pass

        # Retry with relaxed params
        for np, temp in ((min(1024, num_predict * 2), 0.6), (min(1024, num_predict * 2), 0.8)):
            try:
                txt = _try_chat(np, temp)
                if txt:
                    return txt
            except Exception:
                pass
            try:
                txt = _try_generate(np, temp)
                if txt:
                    return txt
            except Exception:
                pass

        return ""

    def _parse_ai_response(self, text: str) -> Dict[str, Any]:
        """
        Parse a JSON response from the model. No dummy fallback; raise if invalid.
        """
        if not text:
            raise ValueError("empty model response")

        # Direct JSON
        try:
            return json.loads(text)
        except Exception:
            pass

        # Try to extract the first JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                pass

        raise ValueError("model returned non-JSON response")

    def _generate_algorithmic_queries(self, kw: List[str], count: int, language: str) -> List[str]:
        """
        Deterministic query generator used when the model output is empty or needs topping up.
        Returns up to `count` unique queries based on the provided keywords and language.
        """
        count = max(0, int(count or 0))
        if count == 0:
            return []
        ar_ok = str(language or "").lower() in ("arabic", "ar", "mixed")
        kw = [k for k in kw if k]
        base_kw = " ".join(kw) if kw else "flood Lebanon"

        seeds = [
            f'{base_kw} flood Lebanon after:2024-01-01',
            f'"{base_kw}" site:gov.lb',
            f'"{base_kw}" filetype:pdf Lebanon',
            f'intitle:flood Lebanon "{kw[0]}"' if kw else 'intitle:flood Lebanon',
            f'{kw[0]} river flood Lebanon' if kw else 'river flood Lebanon',
            f'{kw[0]} coastal flooding Lebanon' if kw else 'coastal flooding Lebanon',
            f'{kw[0]} flash flood Lebanon' if kw else 'flash flood Lebanon',
            f'"{kw[0]}" flood site:*.lb' if kw else 'flood site:*.lb',
            f'"{kw[0]}" precipitation Lebanon 2024..2025' if kw else 'precipitation Lebanon 2024..2025',
        ]
        if ar_ok:
            seeds += [
                'فيضان لبنان بعد:2024-01-01',
                'سيول لبنان ملفtype:pdf',  # tolerant spelling kept
                'نهر الليطاني فيضان',
                (f'"{kw[0]}" فيضان لبنان' if kw else 'فيضانات لبنان'),
            ]

        extra: List[str] = []
        for k in kw[:3] or ["Lebanon"]:
            extra += [
                f'"{k}" flood site:gov.lb',
                f'"{k}" flood site:*.lb after:2024-01-01',
                f'"{k}" flood filetype:pdf',
                f'intitle:"{k}" flood Lebanon',
            ]
            if ar_ok:
                extra += [f'"{k}" سيول لبنان', f'"{k}" فيضان لبنان']

        seen, out = set(), []
        for q in seeds + extra:
            q = (q or "").strip()
            if q and q not in seen:
                seen.add(q)
                out.append(q)
            if len(out) >= count:
                break
        return out

    def generate_search_queries(self, keywords: List[str], context: str = "", count: int = 10, language: str = "mixed") -> Dict[str, Any]:
        """
        Generate up to 100 Google search queries using the current Ollama model.
        Falls back to algorithmic generation if the model returns empty, and tops up
        with algorithmic queries if the model returns fewer than requested.
        """
        count = max(1, min(int(count or 10), 100))
        kw = [str(k).strip() for k in (keywords or []) if str(k).strip()]
        if not kw:
            raise ValueError("keywords cannot be empty")

        prompt = f"""You are an OSINT assistant generating Google search queries for flood-related research in and around Lebanon.

Mission context: {context or "General flood research for Lebanon."}
Keywords: {", ".join(kw)}
Language preference: {language} (mixed = Arabic and English).

Generate {count} diverse, high-signal Google search queries:
- One query per line, no numbering or explanations.
- Use search operators when useful: site:, filetype:, intitle:, after:2024-01-01, "exact phrase".
- Prefer recent info (2024, 2025).
- Include Arabic queries when language is arabic or mixed.
Return only the queries, one per line."""

        text = self._call_ollama(prompt)

        # Handle fenced output
        if text and text.strip().startswith("```"):
            t = text.strip().strip("`")
            nl = t.find("\n")
            text = t[nl + 1 :] if nl != -1 else t

        if not text:
            # Algorithmic fallback to avoid empty results
            queries = self._generate_algorithmic_queries(kw, count, language)
            return {
                "ok": True,
                "model": self.model_name,
                "requested": count,
                "count": len(queries),
                "language": language,
                "context": context,
                "keywords": kw,
                "queries": queries,
                "agent_fallback_queries": queries,
                "supplemented": True,
            }

        # Clean lines: remove bullets, leading numbering like "1.", "2)" and common prefixes
        bullet_re = re.compile(r"^\s*(?:\d+[.)]\s*|[-*•]\s*)")
        lines = [bullet_re.sub("", ln.strip()) for ln in text.splitlines()]
        filtered: List[str] = []
        for ln in lines:
            if not ln:
                continue
            low = ln.lower()
            if any(t in low for t in ("queries:", "here are", "explanation", "strategy", "example", "suggestions")):
                continue
            filtered.append(ln)

        seen, queries = set(), []
        for q in filtered:
            if q not in seen:
                seen.add(q)
                queries.append(q)

        # Top up with algorithmic queries if fewer than requested
        supplements: List[str] = []
        if len(queries) < count:
            need = count - len(queries)
            algo = self._generate_algorithmic_queries(kw, need * 2, language)  # request a few extra to avoid dups
            for q in algo:
                if q not in seen:
                    seen.add(q)
                    supplements.append(q)
                    queries.append(q)
                if len(queries) >= count:
                    break

        queries = queries[:count]
        if not queries:
            # Absolute fallback; should be rare
            queries = self._generate_algorithmic_queries(kw, count, language)
            supplements = queries

        result = {
            "ok": True,
            "model": self.model_name,
            "requested": count,
            "count": len(queries),
            "language": language,
            "context": context,
            "keywords": kw,
            "queries": queries,
        }
        if supplements:
            result["supplemented"] = True
            result["agent_supplements"] = supplements
        return result
def analyze_scraped_article(
    url: str, title: str, content: str, model_name: str = "gpt-oss:20b", context: str = None
) -> Dict[str, Any]:
    """
    Analyze a scraped article, optionally filtering by a custom context/prompt.
    If context is provided, use the AI model to determine relevance to the context.
    """
    agent = FloodAnalysisAgent(model_name=model_name)

    if context:
        # Use the provided context (prompt) directly, formatting in the article title/content
        prompt = f"{context}\n\nArticle Title: {title}\nArticle Content: {content}\n"
        response = agent._call_ollama(prompt)
        # Try to parse as JSON, fallback to raw text
        try:
            extracted_info = json.loads(response)
        except Exception:
            extracted_info = response.strip()
        return {
            "url": url,
            "extracted_info": extracted_info,
            "analyzed_at": str(time.time())
        }

    # Default: use flood relevance logic
    relevance_analysis = agent.is_flood_related(title, content)
    detailed_info = {}
    if relevance_analysis.get("is_relevant", False):
        detailed_info = agent.extract_key_info(title, content)
    return {
        "url": url,
        "relevance_analysis": relevance_analysis,
        "detailed_info": detailed_info,
        "analyzed_at": str(time.time())
    }
# AI Agent for analyzing scraped flood data using Ollama
import requests
import json
import time
from typing import Dict, Any, List

class FloodAnalysisAgent:
    def __init__(self, ollama_url="http://localhost:11434", model_name="llama2"):
        self.ollama_url = ollama_url
        self.model_name = model_name
        
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
        """
        
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
        """
        
        try:
            response = self._call_ollama(prompt)
            return self._parse_ai_response(response)
        except Exception as e:
            return {"error": str(e)}
    
    def _call_ollama(self, prompt: str) -> str:
        """
        Make API call to local Ollama instance
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }
        
        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            raise Exception(f"Ollama API error: {response.status_code}")
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """
        Parse AI response as JSON, with fallback handling
        """
        try:
            # Try to find JSON in the response
            response = response.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "is_relevant": "flood" in response.lower(),
                "confidence": 50,
                "keywords_found": [],
                "summary": "Could not parse AI response properly",
                "category": "parsing_error",
                "raw_response": response
            }

def analyze_scraped_article(url: str, title: str, content: str, model_name: str = "llama2") -> Dict[str, Any]:
    """
    Convenience function to analyze a scraped article
    """
    agent = FloodAnalysisAgent(model_name=model_name)
    
    # Check if flood-related
    relevance_analysis = agent.is_flood_related(title, content)
    
    # If relevant, extract detailed info
    detailed_info = {}
    if relevance_analysis.get("is_relevant", False):
        detailed_info = agent.extract_key_info(title, content)
    
    return {
        "url": url,
        "relevance_analysis": relevance_analysis,
        "detailed_info": detailed_info,
        "analyzed_at": str(time.time())
    }
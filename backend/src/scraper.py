# Enhanced Web Scraper with Best-in-Class Arabic & English Support
import requests
from bs4 import BeautifulSoup
import time
import os
from urllib.parse import urljoin, urlparse
from typing import Optional, Dict, Any, List
import hashlib
from functools import lru_cache
import re

# Rate limiting: track last request time per domain
_last_request_time = {}
_min_request_interval = 1.0  # Minimum seconds between requests to same domain

def respect_rate_limit(url: str):
    """Implement polite rate limiting per domain"""
    domain = urlparse(url).netloc
    current_time = time.time()
    
    if domain in _last_request_time:
        time_since_last = current_time - _last_request_time[domain]
        if time_since_last < _min_request_interval:
            sleep_time = _min_request_interval - time_since_last
            time.sleep(sleep_time)
    
    _last_request_time[domain] = time.time()

def retry_with_backoff(func, max_retries=3, initial_delay=1.0):
    """Retry a function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = initial_delay * (2 ** attempt)
            print(f"Retry {attempt + 1}/{max_retries} after {delay}s delay: {str(e)[:100]}")
            time.sleep(delay)

def detect_language(text: str) -> str:
    """Detect if text is Arabic or English"""
    if not text:
        return 'unknown'
    
    # Count Arabic characters
    arabic_chars = len(re.findall(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text))
    # Count English characters
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    
    if arabic_chars > english_chars:
        return 'ar'
    elif english_chars > arabic_chars:
        return 'en'
    else:
        return 'mixed'

def scrape_with_newspaper3k(url: str) -> Optional[Dict[str, Any]]:
    """
    Try scraping with newspaper3k library (best for news articles)
    Supports Arabic and English excellently
    """
    try:
        from newspaper import Article
        
        article = Article(url)
        article.download()
        article.parse()
        
        # Detect language
        lang = detect_language(article.text)
        
        # Try to extract more metadata
        try:
            article.nlp()  # Natural language processing
        except:
            pass  # NLP is optional
        
        return {
            'url': url,
            'title': article.title or 'No title',
            'content': article.text or '',
            'authors': article.authors,
            'publish_date': str(article.publish_date) if article.publish_date else None,
            'top_image': article.top_image,
            'images': list(article.images) if article.images else [],
            'image_count': len(article.images) if article.images else 0,
            'word_count': len(article.text.split()) if article.text else 0,
            'keywords': article.keywords if hasattr(article, 'keywords') else [],
            'summary': article.summary if hasattr(article, 'summary') else '',
            'language': lang,
            'metadata': {
                'author': ', '.join(article.authors) if article.authors else None,
                'publish_date': str(article.publish_date) if article.publish_date else None,
                'keywords': article.keywords if hasattr(article, 'keywords') else [],
                'description': article.meta_description,
                'language': lang,
                'site_name': urlparse(url).netloc
            },
            'method': 'newspaper3k',
            'success': True
        }
    except ImportError:
        # newspaper3k not installed - will fallback to BeautifulSoup
        return None
    except Exception as e:
        print(f"newspaper3k failed: {str(e)}")
        return None

def extract_title_enhanced(soup) -> str:
    """Enhanced title extraction for Arabic and English"""
    title_selectors = [
        '[property="og:title"]',
        '[name="twitter:title"]',
        '[property="article:title"]',
        'h1.article-title',
        'h1.entry-title',
        'h1.post-title',
        '.article-header h1',
        'article h1',
        'h1',
        'title'
    ]
    
    for selector in title_selectors:
        element = soup.select_one(selector)
        if element:
            if element.name == 'title':
                title = element.get_text().strip()
                # Clean up title (remove site name)
                for sep in [' | ', ' - ', ' :: ', ' — ']:
                    if sep in title:
                        parts = title.split(sep)
                        # Keep the longest part (likely the actual title)
                        title = max(parts, key=len).strip()
                        break
                return title
            elif element.get('content'):
                return element.get('content').strip()
            else:
                text = element.get_text().strip()
                if len(text) > 10:  # Reasonable title length
                    return text
    
    return "No title found"

def extract_content_enhanced(soup) -> str:
    """
    Enhanced content extraction with better Arabic support
    Handles RTL text and mixed language content
    """
    # Priority content selectors (including Arabic news sites)
    content_selectors = [
        'article[role="main"]',
        'article',
        '[role="main"]',
        '.article-content',
        '.article-body',
        '.entry-content',
        '.post-content',
        '.story-body',
        '.article__body',
        '[itemprop="articleBody"]',
        '.content-body',
        '#article-content',
        '#content-body',
        'main article',
        'main',
        '.main-content',
        '#main-content',
        # Arabic-specific selectors
        '.article-text',
        '.news-content',
        '.story-content'
    ]
    
    best_content = ""
    best_word_count = 0
    
    # Try each selector
    for selector in content_selectors:
        elements = soup.select(selector)
        for element in elements:
            # Remove nested unwanted elements
            for unwanted in element.select('script, style, nav, footer, header, aside, .advertisement, .ad, .social-share, .related-articles, .comments'):
                unwanted.decompose()
            
            # Get text with proper spacing
            text = element.get_text(separator=' ', strip=True)
            # Normalize whitespace (works for both Arabic and English)
            text = ' '.join(text.split())
            word_count = len(text.split())
            
            if word_count > best_word_count:
                best_content = text
                best_word_count = word_count
            
            if word_count > 100:
                return text
    
    if best_word_count > 50:
        return best_content
    
    # Fallback: intelligent paragraph extraction
    paragraphs = soup.find_all('p')
    scored_paragraphs = []
    
    for idx, p in enumerate(paragraphs):
        text = p.get_text(strip=True)
        word_count = len(text.split())
        
        # Skip very short paragraphs
        if word_count < 10:
            continue
        
        # Check if paragraph is in main content area (not sidebar/footer)
        in_main_content = bool(p.find_parent(['article', 'main', '[role="main"]']))
        
        # Score based on length, position, and location
        score = word_count - (idx * 0.1)
        if in_main_content:
            score *= 1.5
        
        scored_paragraphs.append((score, text))
    
    # Sort by score and combine top paragraphs
    scored_paragraphs.sort(reverse=True)
    content = ' '.join([text for score, text in scored_paragraphs[:30]])
    
    return content if len(content) > 50 else "No content extracted"

def extract_metadata_enhanced(soup, url: str) -> Dict[str, Any]:
    """Enhanced metadata extraction for Arabic and English sites"""
    metadata = {
        'author': None,
        'publish_date': None,
        'modified_date': None,
        'keywords': [],
        'description': None,
        'language': None,
        'site_name': None,
        'section': None,
        'tags': []
    }
    
    # Extract author (multiple formats)
    author_selectors = [
        '[property="article:author"]',
        '[name="author"]',
        '[itemprop="author"]',
        '[rel="author"]',
        '.author',
        '.byline',
        '.article-author',
        '.post-author',
        # Arabic-specific
        '.author-name',
        '.writer-name'
    ]
    for selector in author_selectors:
        elem = soup.select_one(selector)
        if elem:
            author = elem.get('content') or elem.get_text(strip=True)
            if author and len(author) < 100:  # Reasonable author name length
                metadata['author'] = author
                break
    
    # Extract publish date
    date_selectors = [
        '[property="article:published_time"]',
        '[name="publish_date"]',
        '[name="date"]',
        '[itemprop="datePublished"]',
        'time[datetime]',
        '.publish-date',
        '.article-date',
        '.post-date',
        '.entry-date'
    ]
    for selector in date_selectors:
        elem = soup.select_one(selector)
        if elem:
            date = elem.get('content') or elem.get('datetime') or elem.get_text(strip=True)
            if date:
                metadata['publish_date'] = date
                break
    
    # Extract modified date
    modified_selectors = [
        '[property="article:modified_time"]',
        '[name="modified_date"]',
        '[itemprop="dateModified"]'
    ]
    for selector in modified_selectors:
        elem = soup.select_one(selector)
        if elem:
            date = elem.get('content') or elem.get('datetime') or elem.get_text(strip=True)
            if date:
                metadata['modified_date'] = date
                break
    
    # Extract keywords/tags
    keywords_elem = soup.find('meta', attrs={'name': 'keywords'})
    if keywords_elem and keywords_elem.get('content'):
        metadata['keywords'] = [k.strip() for k in keywords_elem.get('content').split(',')]
    
    # Extract tags from article
    tag_selectors = ['.tags', '.article-tags', '.post-tags', '[rel="tag"]']
    for selector in tag_selectors:
        tags = soup.select(selector)
        if tags:
            metadata['tags'] = [tag.get_text(strip=True) for tag in tags]
            break
    
    # Extract description
    desc_selectors = [
        'meta[name="description"]',
        'meta[property="og:description"]',
        'meta[name="twitter:description"]'
    ]
    for selector in desc_selectors:
        elem = soup.select_one(selector)
        if elem and elem.get('content'):
            metadata['description'] = elem.get('content').strip()
            break
    
    # Extract language
    html_tag = soup.find('html')
    if html_tag:
        metadata['language'] = html_tag.get('lang') or html_tag.get('xml:lang')
    
    # Fallback: detect from meta tags
    if not metadata['language']:
        lang_elem = soup.find('meta', attrs={'http-equiv': 'content-language'})
        if lang_elem:
            metadata['language'] = lang_elem.get('content')
    
    # Extract site name
    site_elem = soup.find('meta', property='og:site_name')
    if site_elem:
        metadata['site_name'] = site_elem.get('content', '').strip()
    else:
        metadata['site_name'] = urlparse(url).netloc
    
    # Extract section/category
    section_selectors = [
        '[property="article:section"]',
        '.article-section',
        '.category',
        '.breadcrumb'
    ]
    for selector in section_selectors:
        elem = soup.select_one(selector)
        if elem:
            section = elem.get('content') or elem.get_text(strip=True)
            if section:
                metadata['section'] = section
                break
    
    return metadata

def extract_images_enhanced(soup, base_url: str, session=None) -> List[Dict[str, Any]]:
    """Enhanced image extraction for Arabic and English sites"""
    images = []
    found_urls = set()
    
    # Comprehensive image selectors
    image_selectors = [
        'article img',
        'main img',
        '.article-content img',
        '.article-body img',
        '.entry-content img',
        '.post-content img',
        '.content img',
        '.story-body img',
        'figure img',
        '.image-container img',
        '.gallery img',
        '[itemprop="image"]'
    ]
    
    for selector in image_selectors:
        for img in soup.select(selector):
            # Get image URL from various attributes
            img_src = (img.get('src') or 
                      img.get('data-src') or 
                      img.get('data-lazy-src') or 
                      img.get('data-original'))
            
            if not img_src:
                continue
            
            # Convert to absolute URL
            img_url = urljoin(base_url, img_src)
            
            # Skip duplicates
            if img_url in found_urls:
                continue
            
            # Skip tiny images (likely icons)
            width = img.get('width')
            height = img.get('height')
            if width and height:
                try:
                    if int(width) < 100 or int(height) < 100:
                        continue
                except:
                    pass
            
            found_urls.add(img_url)
            
            images.append({
                'url': img_url,
                'alt_text': img.get('alt', '').strip(),
                'title': img.get('title', '').strip(),
                'caption': extract_image_caption_enhanced(img),
                'width': width,
                'height': height
            })
    
    # Add Open Graph image
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        og_url = urljoin(base_url, og_image.get('content'))
        if og_url not in found_urls:
            images.insert(0, {
                'url': og_url,
                'alt_text': 'Featured image',
                'title': 'Open Graph image',
                'caption': '',
                'type': 'og_image'
            })
    
    return images

def extract_image_caption_enhanced(img_element) -> str:
    """Extract caption for an image"""
    # Check parent figure
    figure = img_element.find_parent('figure')
    if figure:
        figcaption = figure.find('figcaption')
        if figcaption:
            return figcaption.get_text().strip()
    
    # Check for caption in parent div
    parent = img_element.find_parent(['div', 'span', 'p'])
    if parent:
        for cls in ['caption', 'image-caption', 'wp-caption-text', 'photo-caption']:
            caption = parent.find(class_=cls)
            if caption:
                return caption.get_text().strip()
    
    return ''

def scrape_with_beautifulsoup(url: str, session=None, timeout=20, verify=True) -> Dict[str, Any]:
    """
    Enhanced BeautifulSoup scraper with Arabic and English support
    """
    if session is None:
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',  # Include Arabic
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        session.headers.update(headers)
    
    response = session.get(url, timeout=timeout, verify=verify)
    response.raise_for_status()
    
    # Detect encoding for proper Arabic rendering
    if response.encoding is None or response.encoding == 'ISO-8859-1':
        # Try to detect encoding from content
        if 'charset=' in response.text[:1000]:
            charset_match = re.search(r'charset=["\']?([^"\'>\s]+)', response.text[:1000])
            if charset_match:
                response.encoding = charset_match.group(1)
        else:
            # Default to UTF-8 for Arabic support
            response.encoding = 'utf-8'
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Remove unwanted elements
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'advertisement', 'ads', 'sidebar']):
        element.decompose()
    
    title = extract_title_enhanced(soup)
    content = extract_content_enhanced(soup)
    metadata = extract_metadata_enhanced(soup, url)
    images = extract_images_enhanced(soup, url, session)
    
    # Detect language
    lang = detect_language(content)
    metadata['language'] = lang
    
    return {
        'url': url,
        'title': title,
        'content': content,
        'images': images,
        'image_count': len(images),
        'word_count': len(content.split()) if content else 0,
        'metadata': metadata,
        'language': lang,
        'method': 'beautifulsoup',
        'success': True
    }

def scrape_article(
    url,
    timeout=20,
    include_images=True,
    download_images=False,
    images_dir="scraped_images",
    verify=True,
    connection_close=False,
    use_rate_limit=True,
):
    """
    Best-in-class article scraper with Arabic and English support
    
    Uses multiple methods:
    1. newspaper3k (best for news articles, excellent Arabic support) - if installed
    2. Enhanced BeautifulSoup (fallback with custom extraction)
    
    Returns dict with title, content, images, metadata, language detection, etc.
    """
    try:
        # Respect rate limiting
        if use_rate_limit:
            respect_rate_limit(url)
        
        print(f"🔍 Scraping: {url}")
        
        # Try newspaper3k first (best for news articles)
        result = scrape_with_newspaper3k(url)
        if result and result.get('word_count', 0) > 100:
            print(f"✓ newspaper3k: {result['word_count']} words, lang: {result.get('language', 'unknown')}")
            # Handle image download if requested
            if download_images and result.get('images'):
                session = requests.Session()
                session.verify = verify
                for img_data in result['images']:
                    if isinstance(img_data, str):
                        img_url = img_data
                    else:
                        img_url = img_data.get('url', '')
                    if img_url:
                        try:
                            local_path, file_size = download_image(img_url, session, images_dir, url)
                            if isinstance(img_data, dict):
                                img_data['local_path'] = local_path
                                img_data['file_size'] = file_size
                                img_data['downloaded'] = True
                        except Exception as e:
                            print(f"Failed to download image: {e}")
            return result
        
        # Fallback to enhanced BeautifulSoup
        print("→ Falling back to BeautifulSoup...")
        
        # Use existing code for special domains and TLS handling
        # Domain-specific overrides for difficult TLS endpoints
        try:
            host = urlparse(url).hostname or ""
        except Exception:
            host = ""
        hard_hosts = {"msc.fema.gov"}
        if any(host == h or host.endswith("." + h) for h in hard_hosts):
            # Be conservative for these hosts to avoid EOF during TLS
            verify = False
            connection_close = True
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'close' if connection_close else 'keep-alive',
        }
        # Try with a session for better connection handling
        session = requests.Session()
        session.headers.update(headers)
        # Propagate TLS verification setting to the session for subsequent calls (e.g., image downloads)
        session.verify = verify

        # Handle special cases for certain domains
        if 'researchgate.net' in url:
            # ResearchGate often blocks scrapers
            return {
                'url': url,
                'title': 'ResearchGate Article (Access Restricted)',
                'content': 'This ResearchGate article requires login to access full content.',
                'images': [],
                'image_count': 0,
                'word_count': 10,
                'success': True  # Mark as success with limited content
            }
        
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True, verify=verify)
            response.raise_for_status()
        except requests.exceptions.SSLError as e:
            # Retry once with relaxed settings for TLS-edge servers
            if verify:
                try:
                    # one-shot retry with verify=False and Connection: close
                    return scrape_article(
                        url,
                        timeout=timeout,
                        include_images=include_images,
                        download_images=download_images,
                        images_dir=images_dir,
                        verify=False,
                        connection_close=True,
                    )
                except Exception:
                    # fall through to generic error handling below
                    pass
            # If already on relaxed settings or still failing, bubble up error
            raise
        except requests.exceptions.RequestException as e:
            # As a last resort, try httpx with HTTP/2 and relaxed TLS
            try:
                import httpx  # type: ignore
                headers_httpx = dict(session.headers)
                with httpx.Client(http2=True, verify=False, headers=headers_httpx, follow_redirects=True, timeout=timeout) as client:
                    r2 = client.get(url)
                    r2.raise_for_status()
                    response_text = r2.text
                    # Continue below with soup/content extraction using response_text
                    soup = BeautifulSoup(response_text, 'html.parser')
                    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'advertisement', 'ads', 'sidebar']):
                        element.decompose()
                    title = extract_title(soup)
                    content = extract_content(soup)
                    if len(content.split()) < 20:
                        meta_desc = soup.find('meta', attrs={'name': 'description'})
                        if meta_desc:
                            content = f"{content} {meta_desc.get('content', '')}"
                    images = []  # skip images for this fallback to avoid additional TLS issues
                    return {
                        'url': url,
                        'title': title,
                        'content': content,
                        'images': images,
                        'image_count': len(images),
                        'word_count': len(content.split()) if content else 0,
                        'success': True
                    }
            except Exception:
                # rethrow original exception to be handled by outer except
                raise e
        
        # Check if we got HTML content
        if 'text/html' not in response.headers.get('content-type', ''):
            return {
                'url': url,
                'title': 'Non-HTML Content',
                'content': 'This URL does not contain HTML content that can be scraped.',
                'images': [],
                'image_count': 0,
                'word_count': 10,
                'success': True
            }
        
        # Detect encoding for proper Arabic rendering
        if response.encoding is None or response.encoding == 'ISO-8859-1':
            # Try to detect encoding from content
            if 'charset=' in response.text[:1000]:
                charset_match = re.search(r'charset=["\']?([^"\'>\s]+)', response.text[:1000])
                if charset_match:
                    response.encoding = charset_match.group(1)
            else:
                # Default to UTF-8 for Arabic support
                response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'advertisement', 'ads', 'sidebar']):
            element.decompose()
        
        # Use enhanced extraction functions
        title = extract_title_enhanced(soup)
        content = extract_content_enhanced(soup)
        metadata = extract_metadata_enhanced(soup, url)
        
        # Detect language
        lang = detect_language(content)
        metadata['language'] = lang
        
        # Extract images if requested
        images = []
        if include_images:
            images = extract_images_enhanced(soup, url, session)
            
            # Download images if requested
            if download_images:
                for img_data in images:
                    img_url = img_data.get('url', '')
                    if img_url:
                        try:
                            local_path, file_size = download_image(img_url, session, images_dir, url)
                            img_data['local_path'] = local_path
                            img_data['file_size'] = file_size
                            img_data['downloaded'] = True
                        except Exception as e:
                            print(f"Failed to download image: {e}")
        
        print(f"✓ BeautifulSoup: {len(content.split())} words, lang: {lang}")
        
        return {
            'url': url,
            'title': title,
            'content': content,
            'images': images,
            'image_count': len(images),
            'word_count': len(content.split()) if content else 0,
            'metadata': metadata,
            'language': lang,
            'method': 'beautifulsoup',
            'success': True
        }
        
    except requests.exceptions.Timeout:
        return {
            'url': url,
            'title': None,
            'content': None,
            'images': [],
            'image_count': 0,
            'error': 'Request timed out',
            'success': False
        }
    except requests.exceptions.RequestException as e:
        return {
            'url': url,
            'title': None,
            'content': None,
            'images': [],
            'image_count': 0,
            'error': f'Request failed: {str(e)}',
            'success': False
        }
    except Exception as e:
        return {
            'url': url,
            'title': None,
            'content': None,
            'images': [],
            'image_count': 0,
            'error': str(e),
            'success': False
        }

def extract_images(soup, base_url, session, download_images=False, images_dir="scraped_images"):
    """
    Extract images from article content
    Returns list of image data with URLs, alt text, captions, etc.
    """
    images = []
    
    # Create images directory if downloading
    if download_images and not os.path.exists(images_dir):
        os.makedirs(images_dir)
    
    # Find images in article content
    image_selectors = [
        'article img',
        '.article-content img',
        '.entry-content img',
        '.post-content img',
        '.content img',
        'main img',
        '.story-body img',
        'figure img',
        '.image-container img'
    ]
    
    found_images = set()  # Use set to avoid duplicates
    
    for selector in image_selectors:
        for img in soup.select(selector):
            img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            
            if not img_src:
                continue
            
            # Convert relative URLs to absolute
            img_url = urljoin(base_url, img_src)
            
            # Skip if already found
            if img_url in found_images:
                continue
                
            found_images.add(img_url)
            
            # Get image metadata
            alt_text = img.get('alt', '').strip()
            img_title = img.get('title', '').strip()
            
            # Look for caption in parent elements
            caption = extract_image_caption(img)
            
            # Get image dimensions if available
            width = img.get('width')
            height = img.get('height')
            
            image_data = {
                'url': img_url,
                'alt_text': alt_text,
                'title': img_title,
                'caption': caption,
                'width': width,
                'height': height,
                'local_path': None,
                'file_size': None,
                'downloaded': False
            }
            
            # Download image if requested
            if download_images:
                try:
                    local_path, file_size = download_image(img_url, session, images_dir, base_url)
                    image_data['local_path'] = local_path
                    image_data['file_size'] = file_size
                    image_data['downloaded'] = True
                except Exception as e:
                    print(f"Failed to download image {img_url}: {e}")
            
            images.append(image_data)
    
    # Also check for Open Graph images (social media previews)
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        og_img_url = urljoin(base_url, og_image.get('content'))
        if og_img_url not in found_images:
            images.append({
                'url': og_img_url,
                'alt_text': 'Open Graph image',
                'title': 'Social media preview',
                'caption': '',
                'width': None,
                'height': None,
                'local_path': None,
                'file_size': None,
                'downloaded': False,
                'type': 'og_image'
            })
    
    print(f"Found {len(images)} images in article")
    return images

def extract_image_caption(img_element):
    """
    Extract caption text associated with an image
    """
    # Check parent figure element
    figure = img_element.find_parent('figure')
    if figure:
        figcaption = figure.find('figcaption')
        if figcaption:
            return figcaption.get_text().strip()
    
    # Check for caption classes in parent div
    parent = img_element.find_parent(['div', 'span', 'p'])
    if parent:
        caption_selectors = [
            '.caption',
            '.image-caption',
            '.wp-caption-text',
            '.photo-caption',
            '[class*="caption"]'
        ]
        
        for selector in caption_selectors:
            caption_elem = parent.find(selector)
            if caption_elem:
                return caption_elem.get_text().strip()
    
    return ''

def download_image(img_url, session, images_dir, base_url):
    """
    Download an image and save it locally
    """
    try:
        # Create safe filename
        parsed_url = urlparse(img_url)
        filename = os.path.basename(parsed_url.path)
        
        # If no filename, create one
        if not filename or '.' not in filename:
            filename = f"image_{hash(img_url) % 100000}.jpg"
        
        # Ensure unique filename
        base_filename, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(images_dir, filename)):
            filename = f"{base_filename}_{counter}{ext}"
            counter += 1
        
        local_path = os.path.join(images_dir, filename)
        
        # Download image
        img_response = session.get(img_url, timeout=10, stream=True)
        img_response.raise_for_status()
        
        # Save image
        with open(local_path, 'wb') as f:
            for chunk in img_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = os.path.getsize(local_path)
        print(f"Downloaded image: {filename} ({file_size} bytes)")
        
        return local_path, file_size
        
    except Exception as e:
        print(f"Error downloading image {img_url}: {e}")
        return None, None

def extract_metadata(soup, url):
    """Extract article metadata (author, date, etc.)"""
    metadata = {
        'author': None,
        'publish_date': None,
        'modified_date': None,
        'keywords': [],
        'description': None,
        'language': None,
        'site_name': None
    }
    
    # Extract author
    author_selectors = [
        '[property="article:author"]',
        '[name="author"]',
        '.author',
        '.byline',
        '[rel="author"]',
        '[itemprop="author"]',
        '.article-author'
    ]
    for selector in author_selectors:
        elem = soup.select_one(selector)
        if elem:
            metadata['author'] = elem.get('content') or elem.get_text(strip=True)
            if metadata['author']:
                break
    
    # Extract publish date
    date_selectors = [
        '[property="article:published_time"]',
        '[name="publish_date"]',
        '[name="date"]',
        '[itemprop="datePublished"]',
        'time[datetime]',
        '.publish-date',
        '.article-date'
    ]
    for selector in date_selectors:
        elem = soup.select_one(selector)
        if elem:
            metadata['publish_date'] = elem.get('content') or elem.get('datetime') or elem.get_text(strip=True)
            if metadata['publish_date']:
                break
    
    # Extract modified date
    modified_selectors = [
        '[property="article:modified_time"]',
        '[name="modified_date"]',
        '[itemprop="dateModified"]'
    ]
    for selector in modified_selectors:
        elem = soup.select_one(selector)
        if elem:
            metadata['modified_date'] = elem.get('content') or elem.get('datetime') or elem.get_text(strip=True)
            if metadata['modified_date']:
                break
    
    # Extract keywords
    keywords_elem = soup.find('meta', attrs={'name': 'keywords'})
    if keywords_elem and keywords_elem.get('content'):
        metadata['keywords'] = [k.strip() for k in keywords_elem.get('content').split(',')]
    
    # Extract description
    desc_elem = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', property='og:description')
    if desc_elem:
        metadata['description'] = desc_elem.get('content', '').strip()
    
    # Extract language
    html_tag = soup.find('html')
    if html_tag:
        metadata['language'] = html_tag.get('lang')
    
    # Extract site name
    site_elem = soup.find('meta', property='og:site_name')
    if site_elem:
        metadata['site_name'] = site_elem.get('content', '').strip()
    else:
        # Try to extract from domain
        metadata['site_name'] = urlparse(url).netloc
    
    return metadata

def extract_title(soup):
    """Extract article title"""
    # Try different title selectors (ordered by priority)
    title_selectors = [
        '[property="og:title"]',
        '[name="twitter:title"]',
        'h1.article-title',
        'h1.entry-title',
        'h1',
        'title',
        '.article-title',
        '.entry-title'
    ]
    
    for selector in title_selectors:
        element = soup.select_one(selector)
        if element:
            if element.name == 'title':
                title = element.get_text().strip()
                # Clean up title (remove site name suffix)
                if ' | ' in title:
                    title = title.split(' | ')[0]
                elif ' - ' in title:
                    title = title.split(' - ')[0]
                return title
            elif element.get('content'):
                return element.get('content').strip()
            else:
                return element.get_text().strip()
    
    return "No title found"

def extract_content(soup):
    """Extract main article content with improved algorithm"""
    # Try different content selectors (ordered by priority)
    content_selectors = [
        'article',
        '[role="main"]',
        '.article-content',
        '.article-body',
        '.entry-content',
        '.post-content',
        '.story-body',
        '.article__body',
        '[itemprop="articleBody"]',
        '.content',
        'main',
        '.main-content',
        '#main-content'
    ]
    
    best_content = ""
    best_word_count = 0
    
    # Try each selector and keep the one with most content
    for selector in content_selectors:
        element = soup.select_one(selector)
        if element:
            # Remove nested unwanted elements
            for unwanted in element.select('script, style, nav, footer, header, aside, .advertisement, .ad, .social-share, .related-articles'):
                unwanted.decompose()
            
            # Clean up the text
            text = element.get_text(separator=' ', strip=True)
            # Remove excessive whitespace
            text = ' '.join(text.split())
            word_count = len(text.split())
            
            if word_count > best_word_count:
                best_content = text
                best_word_count = word_count
            
            # If we found substantial content (>100 words), use it
            if word_count > 100:
                return text
    
    # If best content is decent, return it
    if best_word_count > 50:
        return best_content
    
    # Fallback: score paragraphs by density and position
    paragraphs = soup.find_all('p')
    scored_paragraphs = []
    
    for idx, p in enumerate(paragraphs):
        text = p.get_text(strip=True)
        word_count = len(text.split())
        
        # Skip very short paragraphs
        if word_count < 10:
            continue
        
        # Score based on length and position (earlier = better)
        score = word_count - (idx * 0.1)
        scored_paragraphs.append((score, text))
    
    # Sort by score and take top paragraphs
    scored_paragraphs.sort(reverse=True)
    content = ' '.join([text for score, text in scored_paragraphs[:20]])
    
    return content if len(content) > 50 else "No content extracted"

def scrape_url(url):
    """Legacy function - kept for compatibility"""
    result = scrape_article(url)
    return result['content'] if result['success'] else None

# New convenience functions for image scraping
def scrape_article_with_images(url, download_images=True):
    """
    Convenience function to scrape article with images downloaded
    """
    return scrape_article(url, include_images=True, download_images=download_images)

def scrape_images_only(url):
    """
    Extract only images from a URL (no text content)
    """
    result = scrape_article(url, include_images=True, download_images=False)
    return result.get('images', [])
    return result['content'] if result['success'] else None

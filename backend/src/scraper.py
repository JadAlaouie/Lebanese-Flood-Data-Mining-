# Web scraping utilities
import requests
from bs4 import BeautifulSoup
import time
import os
from urllib.parse import urljoin, urlparse

def scrape_article(url, timeout=20, include_images=True, download_images=False, images_dir="scraped_images"):
    """
    Scrape the full article content from a URL including images
    Returns dict with title, content, images, and metadata
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # Try with a session for better connection handling
        session = requests.Session()
        session.headers.update(headers)
        
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
        
        response = session.get(url, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
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
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'advertisement', 'ads', 'sidebar']):
            element.decompose()
        
        # Try to find the main content
        title = extract_title(soup)
        content = extract_content(soup)
        
        # If content is very short, try alternative methods
        if len(content.split()) < 20:
            # Try to get more content from meta description or other sources
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                content = f"{content} {meta_desc.get('content', '')}"
        
        # Extract images if requested
        images = []
        if include_images:
            images = extract_images(soup, url, session, download_images, images_dir)
        
        return {
            'url': url,
            'title': title,
            'content': content,
            'images': images,
            'image_count': len(images),
            'word_count': len(content.split()) if content else 0,
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

def extract_title(soup):
    """Extract article title"""
    # Try different title selectors
    title_selectors = [
        'h1',
        'title',
        '.article-title',
        '.entry-title',
        '[property="og:title"]'
    ]
    
    for selector in title_selectors:
        element = soup.select_one(selector)
        if element:
            if element.name == 'title':
                return element.get_text().strip()
            elif element.get('content'):
                return element.get('content').strip()
            else:
                return element.get_text().strip()
    
    return "No title found"

def extract_content(soup):
    """Extract main article content"""
    # Try different content selectors
    content_selectors = [
        'article',
        '.article-content',
        '.entry-content',
        '.post-content',
        '.content',
        'main',
        '.main-content'
    ]
    
    for selector in content_selectors:
        element = soup.select_one(selector)
        if element:
            # Clean up the text
            text = element.get_text(separator=' ', strip=True)
            if len(text) > 100:  # Only return if substantial content
                return text
    
    # Fallback: get all paragraphs
    paragraphs = soup.find_all('p')
    content = ' '.join([p.get_text(strip=True) for p in paragraphs])
    
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

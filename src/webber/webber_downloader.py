#!/usr/bin/env python3
"""
Webber - Media Downloader
A powerful tool to download images, vectors, and videos from websites.

Author: Sufyan Mughal (sufyanmughal522@gmail.com)
Version: 2.1.1
License: MIT
"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlencode
from tqdm import tqdm
import re
import time
from pathlib import Path
import fontTools.ttLib as ttLib
from io import BytesIO
            
# Import additional dependencies
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import threading
import zipfile
import jsbeautifier
import cssbeautifier
from pathlib import Path

class WebCrawler:
    """A class to manage website crawling and media discovery."""
    
    def __init__(self, start_url, max_depth=3, max_pages=100):
        self.start_url = start_url
        self.max_depth = max_depth
        self.max_pages = max_pages
        
        # Parse the start URL to get the base domain
        parsed = urlparse(start_url)
        self.base_domain = parsed.netloc
        self.base_scheme = parsed.scheme
        
        # Threading-safe sets for tracking
        self.visited_urls = set()
        self.visited_lock = threading.Lock()
        self.image_urls = set()
        self.images_lock = threading.Lock()
        self.vector_urls = set()
        self.vectors_lock = threading.Lock()
        self.video_urls = set()
        self.videos_lock = threading.Lock()
        
        # Progress tracking
        self.pages_processed = 0
        self.progress_lock = threading.Lock()
        self.font_urls = set()
        self.fonts_lock = threading.Lock()
    
    def is_valid_url(self, url):
        """Validate if the provided URL is well-formed and matches the base domain."""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc]) and parsed.netloc == self.base_domain
        except ValueError:
            return False
    
    def is_valid_image_url(self, url):
        """Check if the URL points to a regular image file."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        parsed = urlparse(url)
        return any(parsed.path.lower().endswith(ext) for ext in image_extensions)

    def is_valid_vector_url(self, url):
        """Check if the URL points to an SVG vector file."""
        parsed = urlparse(url)
        return parsed.path.lower().endswith('.svg')

    def is_valid_video_url(self, url):
        """Check if the URL points to a video file."""
        video_extensions = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v'}
        parsed = urlparse(url)
        return any(parsed.path.lower().endswith(ext) for ext in video_extensions)
        
    def is_valid_font_url(self, url):
        """Check if the URL points to a font file."""
        font_extensions = {'.woff', '.ttf', '.otf'}
        parsed = urlparse(url)
        return any(parsed.path.lower().endswith(ext) for ext in font_extensions)

    def normalize_url(self, url):
        """Normalize URL by removing fragments and some query parameters."""
        parsed = urlparse(url)
        if parsed.query:
            params = dict(pair.split('=') for pair in parsed.query.split('&'))
            filtered_params = {k: v for k, v in params.items() 
                            if not any(track in k.lower() 
                                     for track in ['utm_', 'fbclid', 'ref_'])}
            if filtered_params:
                return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(filtered_params)}"
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    def extract_media(self, html, current_url):
        """Extract all valid links, image URLs, vector URLs, and video URLs from HTML content."""
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        images = set()
        vectors = set()
        videos = set()

        # Extract regular links
        for a in soup.find_all('a', href=True):
            url = urljoin(current_url, a['href'])
            if self.is_valid_url(url):
                links.add(self.normalize_url(url))

        # Extract media from various sources
        for element in soup.find_all(['img', 'source', 'picture', 'object', 'embed', 'link']):
            sources = []
            # Check various attributes
            for attr in ['src', 'data-src', 'href']:
                if element.get(attr):
                    sources.append(element[attr])
            if element.get('srcset'):
                sources.extend(src.strip().split()[0] for src in element['srcset'].split(','))
            if element.get('style'):
                bg_matches = re.findall(r'url\(["\']?([^"\'()]+)["\']?\)', element['style'])
                sources.extend(bg_matches)

            # Process all found sources
            for src in sources:
                url = urljoin(current_url, src)
                normalized_url = self.normalize_url(url)
                if self.is_valid_image_url(url):
                    images.add(normalized_url)
                elif self.is_valid_vector_url(url):
                    vectors.add(normalized_url)
                elif self.is_valid_video_url(url):
                    videos.add(normalized_url)
                elif self.is_valid_font_url(url):
                    with self.fonts_lock:
                        self.font_urls.add(normalized_url)

        # Update media sets with thread safety
        with self.images_lock:
            self.image_urls.update(images)
        with self.vectors_lock:
            self.vector_urls.update(vectors)
        with self.videos_lock:
            self.video_urls.update(videos)

        # Look specifically for font files in stylesheet links
        for link in soup.find_all('link', rel='stylesheet'):
            css_url = urljoin(current_url, link.get('href', ''))
            try:
                css_response = requests.get(css_url, timeout=10)
                css_response.raise_for_status()
                # Find font URLs in CSS content
                font_matches = re.findall(r'url\(["\']?([^"\'()]+\.(?:woff|ttf|otf))["\']?\)', css_response.text)
                for font_url in font_matches:
                    full_url = urljoin(css_url, font_url)
                    if self.is_valid_font_url(full_url):
                        with self.fonts_lock:
                            self.font_urls.add(self.normalize_url(full_url))
            except requests.exceptions.RequestException:
                continue

        return links, images, vectors, videos

    def crawl_page(self, url, depth):
        """Crawl a single page and return discovered links and media URLs."""
        if depth > self.max_depth or self.pages_processed >= self.max_pages:
            return set(), set(), set(), set()

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            with self.progress_lock:
                self.pages_processed += 1
                
            return self.extract_media(response.text, url)
            
        except requests.exceptions.RequestException as e:
            print(f"\nError crawling {url}: {e}")
            return set(), set(), set(), set()

    def crawl(self, media_type='images'):
        """
        Crawl the website starting from the initial URL.
        
        Args:
            media_type (str): Type of media to crawl for ('images', 'vectors', 'videos', or 'fonts')
        """
        print(f"Starting crawl from {self.start_url}")
        to_visit = deque([(self.start_url, 0)])  # (url, depth)
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            while to_visit and self.pages_processed < self.max_pages:
                current_url, depth = to_visit.popleft()
                
                with self.visited_lock:
                    if current_url in self.visited_urls:
                        continue
                    self.visited_urls.add(current_url)
                
                print(f"\rCrawling page {self.pages_processed + 1}/{self.max_pages}: {current_url}", end="")
                links, _, _, _ = self.crawl_page(current_url, depth)
                
                for link in links:
                    if link not in self.visited_urls:
                        to_visit.append((link, depth + 1))
        
        if media_type == 'vectors':
            print(f"\nCrawl complete! Found {len(self.vector_urls)} unique vectors across {self.pages_processed} pages")
            return list(self.vector_urls)
        elif media_type == 'videos':
            print(f"\nCrawl complete! Found {len(self.video_urls)} unique videos across {self.pages_processed} pages")
            return list(self.video_urls)
        elif media_type == 'fonts':
            print(f"\nCrawl complete! Found {len(self.font_urls)} unique fonts across {self.pages_processed} pages")
            return list(self.font_urls)
        else:  # images
            print(f"\nCrawl complete! Found {len(self.image_urls)} unique images across {self.pages_processed} pages")
            return list(self.image_urls)

def get_safe_filename(url, media_type='image'):
    """Generate safe filename from URL while preserving extension."""
    clean_url = url.split('?')[0].split('#')[0]
    basename = os.path.basename(clean_url)
    name, ext = os.path.splitext(basename)
    
    if not ext:
        if media_type == 'vector':
            ext = '.svg'  # Only SVG supported
        elif media_type == 'video':
            if '.mp4' in url.lower():
                ext = '.mp4'
            elif '.webm' in url.lower():
                ext = '.webm'
            else:
                ext = '.mp4'  # Default to mp4
        else:  # image
            if '.jpg' in url.lower() or '.jpeg' in url.lower():
                ext = '.jpg'
            elif '.png' in url.lower():
                ext = '.png'
            else:
                ext = '.jpg'  # Default to jpg
    
    safe_name = re.sub(r'[<>:"/\\|?*\s]', '_', name)
    if not safe_name:
        return f"media{ext}"
    if len(safe_name) > 200:
        safe_name = safe_name[:200]
    
    return f"{safe_name}{ext}"

def download_media_from_urls(urls, download_folder, max_size_mb=10, file_types=None, 
                           retry_count=3, media_type='image'):
    """Generic function to download media files from URLs."""
    max_size = max_size_mb * 1024 * 1024
    download_path = Path(download_folder)
    download_path.mkdir(parents=True, exist_ok=True)

    successful = 0
    failed = 0
    replaced = 0

    with tqdm(total=len(urls), desc=f"Downloading {media_type}s") as pbar:
        for url in urls:
            if file_types:
                ext = os.path.splitext(url)[1].lower()
                if ext not in file_types:
                    pbar.update(1)
                    continue

            base_name = get_safe_filename(url, media_type=media_type)
            file_path = download_path / base_name

            if file_path.exists():
                replaced += 1

            for attempt in range(retry_count):
                try:
                    timeout = 30 if media_type == 'video' else 10
                    response = requests.get(url, stream=True, timeout=timeout)
                    response.raise_for_status()

                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > max_size:
                        print(f"\nSkipped {url}: File size exceeds {max_size_mb}MB")
                        break

                    with open(file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    successful += 1
                    break

                except requests.exceptions.RequestException as e:
                    if attempt < retry_count - 1:
                        time.sleep(2 if media_type == 'video' else 1)
                        continue
                    else:
                        print(f"\nFailed to download {url} after {retry_count} attempts: {e}")
                        failed += 1

            pbar.update(1)

    print(f"\nDownload complete!")
    print(f"Successfully downloaded: {successful} {media_type}s")
    print(f"Replaced existing files: {replaced}")
    print(f"Failed downloads: {failed}")
    if successful > 0:
        print(f"Files saved in: {download_path.absolute()}")

def download_from_single_page(url, media_type='image', download_folder=None, 
                            max_size_mb=None, file_types=None, retry_count=3):
    """Download media files from a single webpage."""
    if download_folder is None:
        download_folder = media_type + 's'
    if max_size_mb is None:
        max_size_mb = 500 if media_type == 'video' else 10

    print(f"Fetching {media_type}s from: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve webpage: {url}\nError: {e}")
        return

    crawler = WebCrawler(url, max_depth=1, max_pages=1)
    _, images, vectors, videos = crawler.extract_media(response.text, url)
    
    if media_type == 'vector':
        urls = vectors
    elif media_type == 'video':
        urls = videos
    else:
        urls = images

    if not urls:
        print(f"No {media_type}s found on the webpage.")
        return

    print(f"Found {len(urls)} {media_type}s. Starting download...")
    download_media_from_urls(
        list(urls),
        download_folder,
        max_size_mb,
        file_types,
        retry_count,
        media_type
    )

def convert_font(font_data, from_format, to_format):
    """Convert font from one format to another using fontTools."""
    try:
        # Read the font
        font = ttLib.TTFont(BytesIO(font_data), fontNumber=0)
        
        # Prepare output buffer
        output = BytesIO()
        
        # Save in new format
        font.save(output, to_format)
        
        return output.getvalue()
    except Exception as e:
        print(f"\nError converting font: {str(e)}")
        return None

def download_fonts(url, download_folder=None, max_size_mb=10, file_types=None, 
                   retry_count=3, max_depth=1, max_pages=1):
    """Download and convert fonts from a website."""
    if download_folder is None:
        download_folder = 'fonts'
    
    print(f"Fetching fonts from: {url}")
    
    # Create temporary directories
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace("www.", "")
    site_name = re.sub(r'[<>:"/\\|?*\s]', '_', domain)
    
    temp_dir = Path(f"{download_folder}/temp_{site_name}")
    woff_dir = temp_dir / "woff"
    ttf_dir = temp_dir / "ttf"
    otf_dir = temp_dir / "otf"
    
    for directory in [woff_dir, ttf_dir, otf_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Initialize crawler and get font URLs
    crawler = WebCrawler(url, max_depth=max_depth, max_pages=max_pages)
    if max_depth > 1:
        font_urls = crawler.crawl(media_type='fonts')
    else:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            _, _, _, _ = crawler.extract_media(response.text, url)
            font_urls = list(crawler.font_urls)
        except requests.exceptions.RequestException as e:
            print(f"Failed to retrieve webpage: {url}\nError: {e}")
            return

    if not font_urls:
        print("No fonts found on the webpage.")
        return
    
    print(f"Found {len(font_urls)} fonts. Starting download...")
    
    # Download and convert fonts
    max_size = max_size_mb * 1024 * 1024
    successful = 0
    failed = 0
    
    with tqdm(total=len(font_urls), desc="Processing fonts") as pbar:
        for url in font_urls:
            try:
                # Download font
                response = requests.get(url, stream=True, timeout=10)
                response.raise_for_status()
                
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > max_size:
                    print(f"\nSkipped {url}: File size exceeds {max_size_mb}MB")
                    continue
                
                font_data = response.content
                original_ext = os.path.splitext(url)[1].lower()
                
                # Generate base filename
                base_name = get_safe_filename(url, 'font')
                name_without_ext = os.path.splitext(base_name)[0]
                
                # Convert and save in all formats
                format_dirs = {
                    '.woff': woff_dir,
                    '.ttf': ttf_dir,
                    '.otf': otf_dir
                }
                
                # Save original format
                with open(format_dirs[original_ext] / f"{name_without_ext}{original_ext}", 'wb') as f:
                    f.write(font_data)
                
                # Convert to other formats
                for target_ext, target_dir in format_dirs.items():
                    if target_ext != original_ext:
                        converted = convert_font(font_data, original_ext[1:], target_ext[1:])
                        if converted:
                            with open(target_dir / f"{name_without_ext}{target_ext}", 'wb') as f:
                                f.write(converted)
                
                successful += 1
                
            except Exception as e:
                print(f"\nError processing font from {url}: {str(e)}")
                failed += 1
            
            pbar.update(1)
    
    # Create zip archive
    fonts_dir = Path(download_folder)
    fonts_dir.mkdir(exist_ok=True)
    zip_name = fonts_dir / f"{site_name}-fonts.zip"
    
    print("\nCreating ZIP archive...")
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for folder, _, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(folder, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)
    
    # Clean up temporary directory
    import shutil
    shutil.rmtree(temp_dir)
    
    print(f"\nFont processing complete!")
    print(f"Successfully processed: {successful} fonts")
    print(f"Failed: {failed}")
    if successful > 0:
        print(f"Fonts archive saved as: {zip_name}")

def download_website_code(url):
    """Download and organize website source code."""
    print(f"Downloading source code from: {url}")
    
    try:
        with tqdm(total=5, desc="Website Code Processing") as main_pbar:
            # Get domain name for folder naming
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace("www.", "")
            site_name = re.sub(r'[<>:"/\\|?*\s]', '_', domain)
            
            # Create temporary directory structure
            main_pbar.set_description("Setting up directory structure")
            temp_dir = Path(f"code/{site_name}")
            css_dir = temp_dir / "css"
            js_dir = temp_dir / "js"
            assets_dir = temp_dir / "assets"
            temp_dir.mkdir(parents=True, exist_ok=True)
            css_dir.mkdir(parents=True, exist_ok=True)
            js_dir.mkdir(parents=True, exist_ok=True)
            (assets_dir / "images").mkdir(parents=True, exist_ok=True)
            (assets_dir / "fonts").mkdir(parents=True, exist_ok=True)
            (assets_dir / "other").mkdir(parents=True, exist_ok=True)
            main_pbar.update(1)

            # Download main page
            main_pbar.set_description("Downloading main page")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            main_pbar.update(1)

            # Initialize code files collection
            html_content = soup.prettify()
            code_files = {
                'html': html_content,
                'css': {},
                'js': {}
            }

            # Process CSS files
            main_pbar.set_description("Processing CSS files")
            css_files = set()
            css_links = soup.find_all("link", rel="stylesheet")
            with tqdm(total=len(css_links), desc="Downloading CSS files") as pbar:
                for link in css_links:
                    css_url = urljoin(url, link.get("href", ""))
                    if css_url:
                        try:
                            css_response = requests.get(css_url, timeout=10)
                            css_response.raise_for_status()
                            css_content = cssbeautifier.beautify(css_response.text)
                            css_name = get_safe_filename(css_url, "css")
                            css_files.add(css_name)
                            code_files['css'][css_name] = css_content
                        except Exception as e:
                            print(f"\nError downloading CSS: {css_url} - {str(e)}")
                    pbar.update(1)
            main_pbar.update(1)

            # Process JavaScript files
            main_pbar.set_description("Processing JavaScript files")
            js_files = set()
            js_scripts = soup.find_all("script", src=True)
            with tqdm(total=len(js_scripts), desc="Downloading JavaScript files") as pbar:
                for script in js_scripts:
                    js_url = urljoin(url, script.get("src", ""))
                    if js_url:
                        try:
                            js_response = requests.get(js_url, timeout=10)
                            js_response.raise_for_status()
                            js_content = jsbeautifier.beautify(js_response.text)
                            js_name = get_safe_filename(js_url, "js")
                            js_files.add(js_name)
                            code_files['js'][js_name] = js_content
                        except Exception as e:
                            print(f"\nError downloading JavaScript: {js_url} - {str(e)}")
                    pbar.update(1)
            main_pbar.update(1)

            # Save files
            main_pbar.set_description("Saving processed files")
            
            # Save HTML
            with open(temp_dir / "index.html", 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Save CSS files
            for css_name, css_content in code_files['css'].items():
                css_path = css_dir / css_name
                with open(css_path, 'w', encoding='utf-8') as f:
                    f.write(css_content)

            # Save JavaScript files
            for js_name, js_content in code_files['js'].items():
                js_path = js_dir / js_name
                with open(js_path, 'w', encoding='utf-8') as f:
                    f.write(js_content)

            # Update HTML paths
            soup = BeautifulSoup(html_content, 'html.parser')
            for link in soup.find_all("link", rel="stylesheet"):
                if link.get("href"):
                    css_name = get_safe_filename(urljoin(url, link["href"]), "css")
                    if css_name in css_files:
                        link["href"] = f"css/{css_name}"

            for script in soup.find_all("script", src=True):
                if script.get("src"):
                    js_name = get_safe_filename(urljoin(url, script["src"]), "js")
                    if js_name in js_files:
                        script["src"] = f"js/{js_name}"

            # Save updated HTML with fixed paths
            with open(temp_dir / "index.html", 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            main_pbar.update(1)

            # Create zip archive
            main_pbar.set_description("Creating zip archive")
            code_dir = Path('code')
            code_dir.mkdir(exist_ok=True)
            zip_name = code_dir / f"{site_name}-source-code.zip"
            # Get list of all files to zip
            files_to_zip = []
            for folder, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(folder, file)
                    files_to_zip.append((file_path, os.path.relpath(file_path, temp_dir)))

            # Create zip archive
            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                with tqdm(total=len(files_to_zip), desc="Adding files to archive") as pbar:
                    for file_path, arcname in files_to_zip:
                        zipf.write(file_path, arcname)
                        pbar.update(1)

            # Clean up temporary directory
            main_pbar.set_description("Cleaning up")
            import shutil
            shutil.rmtree(temp_dir)
            
            print(f"\nWebsite code downloaded successfully!")
            print(f"Source code saved as: {zip_name}")

    except Exception as e:
        print(f"\nError downloading website code: {str(e)}")

def download_with_crawler(url, media_type='image', download_folder=None,
                        max_size_mb=None, file_types=None, retry_count=3,
                        max_depth=3, max_pages=100):
    """Download media files by crawling through website pages."""
    if download_folder is None:
        download_folder = media_type + 's'
    if max_size_mb is None:
        max_size_mb = 500 if media_type == 'video' else 10

    crawler = WebCrawler(url, max_depth=max_depth, max_pages=max_pages)
    urls = crawler.crawl(media_type=media_type)
    
    if not urls:
        print(f"No {media_type}s found while crawling.")
        return
    
    download_media_from_urls(
        urls,
        download_folder,
        max_size_mb,
        file_types,
        retry_count,
        media_type
            )

def main():
    print("\nWebber - Media Downloader")
    print("Author: Sufyan Mughal (sufyanmughal522@gmail.com)")
    
    while True:
        print("\nSelect Mode:")
        print("1. Download images from single page")
        print("2. Download vectors from single page")
        print("3. Download videos from single page")
        print("4. Download fonts from single page")
        print("5. Crawl website for images")
        print("6. Crawl website for vectors")
        print("7. Crawl website for videos")
        print("8. Crawl website for fonts")
        print("9. Download website code")
        print("10. Exit")
        
        choice = input("\nSelect mode (1-10): ").strip()
        
        if choice == "10":
            break
            
        if choice not in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            print("Invalid choice. Please select 1-10.")
            continue
            
        website_url = input("Enter the URL of the website: ")
        
        # Handle different media types
        media_type = 'image'
        if choice in ["2", "6"]:
            media_type = 'vector'
        elif choice in ["3", "7"]:
            media_type = 'video'
        elif choice in ["4", "8"]:
            media_type = 'font'
            
        # Get size limit
        default_size = 500 if media_type == 'video' else 10
        max_size = input(f"Enter maximum file size in MB (default {default_size}): ")
        max_size = int(max_size) if max_size.isdigit() else default_size

        # Get file types
        extensions_map = {
            'image': '.jpg,.png,.gif,.webp',
            'vector': '.svg',  # Only SVG supported
            'video': '.mp4,.webm,.mov',
            'font': '.woff,.ttf,.otf'
        }
        file_types_input = input(f"Enter allowed file extensions (e.g., {extensions_map[media_type]}) or press Enter for all: ")
        file_types = [ext.strip().lower() for ext in file_types_input.split(',')] if file_types_input else None

        # Handle different modes
        if choice in ["1", "2", "3", "4"]:  # Single page downloads
            download_from_single_page(
                website_url,
                media_type=media_type,
                max_size_mb=max_size,
                file_types=file_types
            )
        elif choice == "9":  # Download website code
            download_website_code(website_url)
        elif choice == "4":  # Download fonts from single page
            max_size = input(f"Enter maximum font file size in MB (default 10): ")
            max_size = int(max_size) if max_size.isdigit() else 10
            file_types = [ext.strip() for ext in extensions_map['font'].split(',')]
            download_fonts(website_url, max_size_mb=max_size, file_types=file_types)
        else:  # Crawl website (choices 5, 6, 7, 8)
            max_depth = input("Enter maximum crawl depth (default 3): ")
            max_depth = int(max_depth) if max_depth.isdigit() else 3

            max_pages = input("Enter maximum pages to crawl (default 100): ")
            max_pages = int(max_pages) if max_pages.isdigit() else 100
            
            if choice == "8":  # Crawl for fonts
                download_fonts(
                    website_url,
                    max_size_mb=max_size,
                    file_types=file_types,
                    max_depth=max_depth,
                    max_pages=max_pages
                )
            else:  # Crawl for other media
                download_with_crawler(
                    website_url,
                    media_type=media_type,
                    max_size_mb=max_size,
                    file_types=file_types,
                    max_depth=max_depth,
                    max_pages=max_pages
                )

if __name__ == "__main__":
    main()

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlencode
from tqdm import tqdm
import re
import time
from pathlib import Path
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import threading

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
        self.video_urls = set()
        self.videos_lock = threading.Lock()
        
        # Progress tracking
        self.pages_processed = 0
        self.progress_lock = threading.Lock()
    
    def is_valid_url(self, url):
        """Validate if the provided URL is well-formed and matches the base domain."""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc]) and parsed.netloc == self.base_domain
        except ValueError:
            return False
    
    def is_valid_image_url(self, url):
        """Check if the URL points to an image file."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
        parsed = urlparse(url)
        return any(parsed.path.lower().endswith(ext) for ext in image_extensions)

    def is_valid_video_url(self, url):
        """Check if the URL points to a video file."""
        video_extensions = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v'}
        parsed = urlparse(url)
        return any(parsed.path.lower().endswith(ext) for ext in video_extensions)

    def normalize_url(self, url):
        """Normalize URL by removing fragments and some query parameters."""
        parsed = urlparse(url)
        # Keep only essential query parameters (if any)
        if parsed.query:
            params = dict(pair.split('=') for pair in parsed.query.split('&'))
            # Filter out tracking parameters
            filtered_params = {k: v for k, v in params.items() 
                            if not any(track in k.lower() 
                                     for track in ['utm_', 'fbclid', 'ref_'])}
            if filtered_params:
                return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(filtered_params)}"
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    def extract_media(self, html, current_url):
        """Extract all valid links, image URLs, and video URLs from HTML content."""
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        images = set()
        videos = set()

        # Extract regular links
        for a in soup.find_all('a', href=True):
            url = urljoin(current_url, a['href'])
            if self.is_valid_url(url):
                links.add(self.normalize_url(url))

        # Extract images from various sources
        for img in soup.find_all(['img', 'source', 'picture']):
            # Check src, data-src, srcset attributes
            sources = []
            if img.get('src'):
                sources.append(img['src'])
            if img.get('data-src'):
                sources.append(img['data-src'])
            if img.get('srcset'):
                sources.extend(src.strip().split()[0] for src in img['srcset'].split(','))
            
            # Also check background-image in style attributes
            if img.get('style'):
                bg_matches = re.findall(r'url\(["\']?([^"\'()]+)["\']?\)', img['style'])
                sources.extend(bg_matches)

            # Process all found sources
            for src in sources:
                img_url = urljoin(current_url, src)
                if self.is_valid_image_url(img_url):
                    images.add(self.normalize_url(img_url))

        # Extract videos from various sources
        for video in soup.find_all(['video', 'source']):
            sources = []
            if video.get('src'):
                sources.append(video['src'])
            if video.get('data-src'):
                sources.append(video['data-src'])
            
            # Check type attribute for video content
            if video.get('type', '').startswith('video/'):
                if video.get('src'):
                    sources.append(video['src'])

            # Process all found video sources
            for src in sources:
                video_url = urljoin(current_url, src)
                if self.is_valid_video_url(video_url):
                    videos.add(self.normalize_url(video_url))

        return links, images, videos

    def crawl_page(self, url, depth):
        """Crawl a single page and return discovered links, images, and videos."""
        if depth > self.max_depth or self.pages_processed >= self.max_pages:
            return set(), set(), set()

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            with self.progress_lock:
                self.pages_processed += 1
                
            links, images, videos = self.extract_media(response.text, url)
            
            # Update media URLs
            with self.images_lock:
                self.image_urls.update(images)
            with self.videos_lock:
                self.video_urls.update(videos)
            
            return links, images, videos
            
        except requests.exceptions.RequestException as e:
            print(f"\nError crawling {url}: {e}")
            return set(), set(), set()

    def crawl(self, media_type='images'):
        """
        Crawl the website starting from the initial URL.
        
        Args:
            media_type (str): Type of media to crawl for ('images' or 'videos')
        """
        print(f"Starting crawl from {self.start_url}")
        to_visit = deque([(self.start_url, 0)])  # (url, depth)
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            while to_visit and self.pages_processed < self.max_pages:
                current_url, depth = to_visit.popleft()
                
                # Skip if already visited
                with self.visited_lock:
                    if current_url in self.visited_urls:
                        continue
                    self.visited_urls.add(current_url)
                
                # Crawl the page
                print(f"\rCrawling page {self.pages_processed + 1}/{self.max_pages}: {current_url}", end="")
                links, images, videos = self.crawl_page(current_url, depth)
                
                # Add new links to visit
                for link in links:
                    if link not in self.visited_urls:
                        to_visit.append((link, depth + 1))
        
        if media_type == 'videos':
            print(f"\nCrawl complete! Found {len(self.video_urls)} unique videos across {self.pages_processed} pages")
            return list(self.video_urls)
        else:
            print(f"\nCrawl complete! Found {len(self.image_urls)} unique images across {self.pages_processed} pages")
            return list(self.image_urls)

def get_safe_filename(url, media_type='image'):
    """
    Generate a safe filename from URL while preserving extension.
    
    Args:
        url (str): The URL to generate filename from
        media_type (str): Type of media ('image' or 'video')
    """
    # Parse URL and remove query parameters
    clean_url = url.split('?')[0].split('#')[0]
    
    # Get the base filename
    basename = os.path.basename(clean_url)
    
    # Split into name and extension
    name, ext = os.path.splitext(basename)
    if not ext:
        # Try to guess extension from URL
        if media_type == 'video':
            if '.mp4' in url.lower():
                ext = '.mp4'
            elif '.webm' in url.lower():
                ext = '.webm'
            elif '.mov' in url.lower():
                ext = '.mov'
            else:
                ext = '.mp4'  # Default to mp4
        else:  # image
            if '.jpg' in url.lower() or '.jpeg' in url.lower():
                ext = '.jpg'
            elif '.png' in url.lower():
                ext = '.png'
            elif '.gif' in url.lower():
                ext = '.gif'
            elif '.webp' in url.lower():
                ext = '.webp'
            else:
                ext = '.jpg'  # Default to jpg
    
    # Remove invalid characters and spaces
    safe_name = re.sub(r'[<>:"/\\|?*\s]', '_', name)
    
    # Ensure the filename isn't empty and isn't too long
    if not safe_name:
        return f"media{ext}"
    if len(safe_name) > 200:  # Limit filename length
        safe_name = safe_name[:200]
    
    return f"{safe_name}{ext}"

def download_from_single_page(url, download_folder='images', max_size_mb=10, file_types=None, retry_count=3):
    """
    Download images from a single webpage without crawling.
    
    Args:
        url (str): The webpage URL to download images from
        download_folder (str): Folder to save downloaded images
        max_size_mb (int): Maximum file size in MB for each image
        file_types (list): List of allowed file extensions (e.g., ['.jpg', '.png'])
        retry_count (int): Number of retries for failed downloads
    """
    print(f"Fetching images from: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve webpage: {url}\nError: {e}")
        return

    # Parse the webpage and find images
    soup = BeautifulSoup(response.text, 'html.parser')
    image_urls = set()

    # Find images in various tags and attributes
    for img in soup.find_all(['img', 'source', 'picture']):
        sources = []
        if img.get('src'):
            sources.append(img['src'])
        if img.get('data-src'):
            sources.append(img['data-src'])
        if img.get('srcset'):
            sources.extend(src.strip().split()[0] for src in img['srcset'].split(','))
        
        if img.get('style'):
            bg_matches = re.findall(r'url\(["\']?([^"\'()]+)["\']?\)', img['style'])
            sources.extend(bg_matches)

        for src in sources:
            img_url = urljoin(url, src)
            image_urls.add(img_url)

    if not image_urls:
        print("No images found on the webpage.")
        return

    print(f"Found {len(image_urls)} images. Starting download...")
    download_images_from_urls(list(image_urls), download_folder, max_size_mb, file_types, retry_count)

def download_from_single_page_videos(url, download_folder='videos', max_size_mb=500, file_types=None, retry_count=3):
    """
    Download videos from a single webpage without crawling.
    
    Args:
        url (str): The webpage URL to download videos from
        download_folder (str): Folder to save downloaded videos
        max_size_mb (int): Maximum file size in MB for each video
        file_types (list): List of allowed file extensions (e.g., ['.mp4', '.webm'])
        retry_count (int): Number of retries for failed downloads
    """
    print(f"Fetching videos from: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve webpage: {url}\nError: {e}")
        return

    # Parse the webpage and find videos
    soup = BeautifulSoup(response.text, 'html.parser')
    video_urls = set()

    # Find videos in various tags and attributes
    for video in soup.find_all(['video', 'source']):
        sources = []
        if video.get('src'):
            sources.append(video['src'])
        if video.get('data-src'):
            sources.append(video['data-src'])
        
        # Check type attribute for video content
        if video.get('type', '').startswith('video/'):
            if video.get('src'):
                sources.append(video['src'])

        for src in sources:
            video_url = urljoin(url, src)
            if any(video_url.lower().endswith(ext) for ext in ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.m4v']):
                video_urls.add(video_url)

    if not video_urls:
        print("No videos found on the webpage.")
        return

    print(f"Found {len(video_urls)} videos. Starting download...")
    download_videos_from_urls(list(video_urls), download_folder, max_size_mb, file_types, retry_count)

def download_with_crawler(url, download_folder='images', max_size_mb=10, file_types=None, 
                         retry_count=3, max_depth=3, max_pages=100):
    """
    Download images by crawling through website pages.
    
    Args:
        url (str): The webpage URL to start crawling from
        download_folder (str): Folder to save downloaded images
        max_size_mb (int): Maximum file size in MB for each image
        file_types (list): List of allowed file extensions (e.g., ['.jpg', '.png'])
        retry_count (int): Number of retries for failed downloads
        max_depth (int): Maximum depth for crawling links
        max_pages (int): Maximum number of pages to crawl
    """
    crawler = WebCrawler(url, max_depth=max_depth, max_pages=max_pages)
    image_urls = crawler.crawl()
    
    if not image_urls:
        print("No images found while crawling.")
        return
    
    download_images_from_urls(image_urls, download_folder, max_size_mb, file_types, retry_count)

def download_with_crawler_videos(url, download_folder='videos', max_size_mb=500, file_types=None, 
                               retry_count=3, max_depth=3, max_pages=100):
    """
    Download videos by crawling through website pages.
    
    Args:
        url (str): The webpage URL to start crawling from
        download_folder (str): Folder to save downloaded videos
        max_size_mb (int): Maximum file size in MB for each video
        file_types (list): List of allowed file extensions (e.g., ['.mp4', '.webm'])
        retry_count (int): Number of retries for failed downloads
        max_depth (int): Maximum depth for crawling links
        max_pages (int): Maximum number of pages to crawl
    """
    crawler = WebCrawler(url, max_depth=max_depth, max_pages=max_pages)
    video_urls = crawler.crawl(media_type='videos')
    
    if not video_urls:
        print("No videos found while crawling.")
        return
    
    download_videos_from_urls(video_urls, download_folder, max_size_mb, file_types, retry_count)

def download_images_from_urls(image_urls, download_folder='images', max_size_mb=10, 
                            file_types=None, retry_count=3):
    """
    Download images from a list of URLs.
    
    Args:
        image_urls (list): List of image URLs to download
        download_folder (str): Folder to save downloaded images
        max_size_mb (int): Maximum file size in MB for each image
        file_types (list): List of allowed file extensions (e.g., ['.jpg', '.png'])
        retry_count (int): Number of retries for failed downloads
    """
    # Convert max_size to bytes
    max_size = max_size_mb * 1024 * 1024

    # Create download folder
    download_path = Path(download_folder)
    download_path.mkdir(parents=True, exist_ok=True)

    # Track download statistics
    successful = 0
    failed = 0
    replaced = 0

    # Create progress bar for downloads
    with tqdm(total=len(image_urls), desc="Downloading images") as pbar:
        for img_url in image_urls:
            # Check file type if specified
            if file_types:
                ext = os.path.splitext(img_url)[1].lower()
                if ext not in file_types:
                    pbar.update(1)
                    continue

            # Generate safe filename
            base_name = get_safe_filename(img_url, media_type='image')
            img_path = download_path / base_name

            # Check if file exists
            if img_path.exists():
                replaced += 1

            # Try downloading with retries
            for attempt in range(retry_count):
                try:
                    response = requests.get(img_url, stream=True, timeout=10)
                    response.raise_for_status()

                    # Check file size
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > max_size:
                        print(f"\nSkipped {img_url}: File size exceeds {max_size_mb}MB")
                        break

                    # Download the image
                    with open(img_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    successful += 1
                    break

                except requests.exceptions.RequestException as e:
                    if attempt < retry_count - 1:
                        time.sleep(1)  # Wait before retrying
                        continue
                    else:
                        print(f"\nFailed to download {img_url} after {retry_count} attempts: {e}")
                        failed += 1

            pbar.update(1)

    print(f"\nDownload complete!")
    print(f"Successfully downloaded: {successful} images")
    print(f"Replaced existing files: {replaced}")
    print(f"Failed downloads: {failed}")
    if successful > 0:
        print(f"Images saved in: {download_path.absolute()}")

def download_videos_from_urls(video_urls, download_folder='videos', max_size_mb=500, 
                            file_types=None, retry_count=3):
    """
    Download videos from a list of URLs.
    
    Args:
        video_urls (list): List of video URLs to download
        download_folder (str): Folder to save downloaded videos
        max_size_mb (int): Maximum file size in MB for each video
        file_types (list): List of allowed file extensions (e.g., ['.mp4', '.webm'])
        retry_count (int): Number of retries for failed downloads
    """
    # Convert max_size to bytes
    max_size = max_size_mb * 1024 * 1024

    # Create download folder
    download_path = Path(download_folder)
    download_path.mkdir(parents=True, exist_ok=True)

    # Track download statistics
    successful = 0
    failed = 0
    replaced = 0

    # Create progress bar for downloads
    with tqdm(total=len(video_urls), desc="Downloading videos") as pbar:
        for video_url in video_urls:
            # Check file type if specified
            if file_types:
                ext = os.path.splitext(video_url)[1].lower()
                if ext not in file_types:
                    pbar.update(1)
                    continue

            # Generate safe filename
            base_name = get_safe_filename(video_url, media_type='video')
            video_path = download_path / base_name

            # Check if file exists
            if video_path.exists():
                replaced += 1

            # Try downloading with retries
            for attempt in range(retry_count):
                try:
                    response = requests.get(video_url, stream=True, timeout=30)  # Longer timeout for videos
                    response.raise_for_status()

                    # Check file size
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > max_size:
                        print(f"\nSkipped {video_url}: File size exceeds {max_size_mb}MB")
                        break

                    # Download the video
                    with open(video_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    successful += 1
                    break

                except requests.exceptions.RequestException as e:
                    if attempt < retry_count - 1:
                        time.sleep(2)  # Longer wait for videos
                        continue
                    else:
                        print(f"\nFailed to download {video_url} after {retry_count} attempts: {e}")
                        failed += 1

            pbar.update(1)

    print(f"\nDownload complete!")
    print(f"Successfully downloaded: {successful} videos")  # Changed to videos
    print(f"Replaced existing files: {replaced}")
    print(f"Failed downloads: {failed}")
    if successful > 0:
        print(f"Videos saved in: {download_path.absolute()}")  # Changed to videos

if __name__ == "__main__":
    while True:
        print("\nMedia Downloader")
        print("1. Download images from single page")
        print("2. Download videos from single page")
        print("3. Crawl website for images")
        print("4. Crawl website for videos")
        print("5. Exit")
        
        choice = input("\nSelect mode (1-5): ").strip()
        
        if choice == "5":
            break
            
        if choice not in ["1", "2", "3", "4"]:
            print("Invalid choice. Please select 1-5.")
            continue
            
        website_url = input("Enter the URL of the website: ")
        
        # Handle images (choices 1, 3)
        if choice in ["1", "3"]:
            max_size = input("Enter maximum file size in MB (default 10): ")
            max_size = int(max_size) if max_size.isdigit() else 10

            file_types_input = input("Enter allowed file extensions (e.g., .jpg,.png) or press Enter for all: ")
            file_types = [ext.strip().lower() for ext in file_types_input.split(',')] if file_types_input else None

            if choice == "1":
                download_from_single_page(
                    website_url,
                    max_size_mb=max_size,
                    file_types=file_types
                )
            else:  # choice == "3"
                max_depth = input("Enter maximum crawl depth (default 3): ")
                max_depth = int(max_depth) if max_depth.isdigit() else 3

                max_pages = input("Enter maximum pages to crawl (default 100): ")
                max_pages = int(max_pages) if max_pages.isdigit() else 100
                
                download_with_crawler(
                    website_url,
                    max_size_mb=max_size,
                    file_types=file_types,
                    max_depth=max_depth,
                    max_pages=max_pages
                )
        
        # Handle videos (choices 2, 4)
        else:
            max_size = input("Enter maximum file size in MB (default 500): ")
            max_size = int(max_size) if max_size.isdigit() else 500

            file_types_input = input("Enter allowed file extensions (e.g., .mp4,.webm) or press Enter for all: ")
            file_types = [ext.strip().lower() for ext in file_types_input.split(',')] if file_types_input else None

            if choice == "2":
                download_from_single_page_videos(
                    website_url,
                    max_size_mb=max_size,
                    file_types=file_types
                )
            else:  # choice == "4"
                max_depth = input("Enter maximum crawl depth (default 3): ")
                max_depth = int(max_depth) if max_depth.isdigit() else 3

                max_pages = input("Enter maximum pages to crawl (default 100): ")
                max_pages = int(max_pages) if max_pages.isdigit() else 100
                
                download_with_crawler_videos(
                    website_url,
                    max_size_mb=max_size,
                    file_types=file_types,
                    max_depth=max_depth,
                    max_pages=max_pages
                )

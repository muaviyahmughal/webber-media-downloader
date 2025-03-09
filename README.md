# Webber Website Media Downloader

A powerful Python tool to download images, vectors, videos, and website source code.

## Features

- Download media from a single webpage or crawl entire websites
- Support for multiple media types:
  - Images (jpg, jpeg, png, gif, webp)
  - Vector graphics (svg)
  - Videos (mp4, webm, mov, avi, mkv, m4v)
- Download website source code with proper organization
- Multi-threaded crawling for better performance
- Progress bars for all operations
- Configurable download settings
- File size limits and type filtering

## Installation

```bash
# Clone the repository
git clone https://github.com/sufyanmughal/webber-website-downloader.git
cd webber-website-downloader

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install the package
pip install -e .
```

## Usage

After installation, you can use the `webber` command-line tool:

```bash
webber
```

This will launch an interactive menu with the following options:

1. Download images from single page
2. Download vectors from single page
3. Download videos from single page
4. Crawl website for images
5. Crawl website for vectors
6. Crawl website for videos
7. Download website code
8. Exit

## Configuration Options

- **File Size Limits**: Set maximum file size for downloads (default: 10MB for images/vectors, 500MB for videos)
- **File Types**: Filter downloads by specific file extensions
- **Crawl Depth**: Set how deep to crawl website links (for crawler modes)
- **Page Limit**: Set maximum number of pages to crawl

## Output Structure

- Images are saved to `./images/`
- Vectors are saved to `./vectors/`
- Videos are saved to `./videos/`
- Website code is saved to `./code/{domain}/` and archived as `{domain}-source-code.zip`

## Author

Sufyan Mughal (sufyanmughal522@gmail.com)

## License

MIT License

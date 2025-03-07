# Changelog

All notable changes to Webber Media Downloader will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2025-03-08

### Added
- Website code download feature
  - Downloads HTML, CSS, and JavaScript files
  - Maintains original website structure
  - Formats code for readability using jsbeautifier
  - Creates organized zip archive with website source code
  - Supports downloading external stylesheets and scripts
  - Updates file paths to maintain local references

## [2.0.0] - 2025-03-07

### Added
- Vector file support (.svg, .ai, .eps)
- Dedicated vector downloading options in menu
- Separate 'vectors' folder for downloads
- Vector-specific file handling and validation
- Enhanced media type detection

### Changed
- Renamed project from "Media Downloader" to "Webber"
- Renamed main script from download_images.py to webber-downloader.py
- Improved documentation with vector support
- Enhanced file organization with dedicated folders
- Refactored WebCrawler class for better media type handling

### Fixed
- File extension detection improvements
- Better error handling for different media types

## [1.0.0] - 2025-03-07

### Added
- Initial release
- Support for downloading images and videos
- Single page and crawl modes
- Progress tracking with status bars
- Configurable download options:
  - Maximum file size limits
  - File type filtering
  - Crawl depth and page limits
- Automatic file naming and organization
- Retry mechanism for failed downloads

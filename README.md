# Webber - Media Downloader

A powerful tool to download images, vectors, and videos from websites, with support for both single-page downloads and website crawling.

## 🚀 Getting Started (Beginner's Guide)

### Prerequisites

1. **Install Python** (Complete Beginner's Guide)
   - Go to [Python's official website](https://www.python.org/downloads/)
   - Click the "Download Python" button (get the latest version)
   - During installation, **IMPORTANT**: Check ✅ "Add Python to PATH"
   - To verify installation, open Command Prompt (Windows) or Terminal (Mac/Linux):
     ```bash
     python --version
     ```
   - You should see something like `Python 3.x.x`

2. **Download This Project**
   - Click the green "Code" button above
   - Select "Download ZIP"
   - Extract the ZIP file to a location you can find easily

### Installation Steps (with Pictures)

1. **Open Terminal/Command Prompt**
   - Windows: Press `Win + R`, type `cmd`, press Enter
   - Mac: Press `Cmd + Space`, type `terminal`, press Enter

2. **Navigate to Project Directory**
   ```bash
   # Windows example (adjust the path to where you extracted the files)
   cd C:\Users\YourName\Downloads\webber-media-downloader
   
   # Mac/Linux example
   cd ~/Downloads/webber-media-downloader
   ```

3. **Create Virtual Environment** (Optional but Recommended)
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate it:
   # Windows:
   venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   ```

4. **Install Required Packages**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Script 🎬

1. **Start the Program**
   ```bash
   python webber-downloader.py
   ```

2. **Using the Menu**
   - You'll see this menu:
     ```
     1. Download images from single page
     2. Download vectors from single page
     3. Download videos from single page
     4. Crawl website for images
     5. Crawl website for vectors
     6. Crawl website for videos
     7. Download website code
     8. Exit
     ```
   - Type the number (1-7) for what you want to do
   - Press Enter

3. **Example: Downloading Website Code**
   - Choose option 7
   - Enter the website URL
   - The code will be downloaded and organized into a zip file with:
     ```
     website_name/
     ├── index.html
     ├── css/
     │   └── (formatted CSS files)
     ├── js/
     │   └── (formatted JavaScript files)
     ├── assets/
     │   ├── images/
     │   ├── fonts/
     │   └── other/
     ```

4. **Example: Downloading Vectors**
   - Choose option 2
   - Paste the website URL (right-click to paste in terminal)
   - Enter maximum file size if needed (default 10MB)
   - Optionally specify file types (e.g., .svg,.ai,.eps)
   - Your vectors will download to the 'vectors' folder!

### Common Issues & Solutions 🔧

1. **"Python not found" Error**
   - Solution: Make sure you checked "Add Python to PATH" during installation
   - Try restarting your computer

2. **"pip not found" Error**
   - Solution: Try using:
     ```bash
     python -m pip install -r requirements.txt
     ```

3. **Permission Errors**
   - Solution: Run terminal/command prompt as administrator

4. **Download Errors**
   - Check your internet connection
   - Make sure the website allows downloading
   - Try again with different file types

## 🎯 Features

### Media Downloads

- Download media from a single webpage or crawl entire websites
- Support for multiple file formats:
  - Images: jpg, jpeg, png, gif, webp
  - Vectors: svg, ai, eps
  - Videos: mp4, webm, mov, avi, mkv, m4v
- Configurable download options:
  - Maximum file size limits
  - File type filtering
  - Crawl depth and page limits
- Progress tracking with status bars
- Automatic file naming and organization
- Separate folders for images, vectors, and videos
- Retry mechanism for failed downloads

### Website Code Download
- Download complete website source code
- Automatically organize files in a clean structure
- Format HTML, CSS, and JavaScript for readability
- Download external stylesheets and scripts
- Update file paths to maintain local references
- Create organized zip archive of website code

## ⚙️ Configuration

- Default image/vector size limit: 10MB
- Default video size limit: 500MB
- Default crawl depth: 3 levels
- Default max pages: 100 pages
- Download retries: 3 attempts

## 📦 Dependencies

- beautifulsoup4: HTML parsing
- requests: HTTP requests
- tqdm: Progress bars
- jsbeautifier: JavaScript code formatting
- cssbeautifier: CSS code formatting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Contact

For questions, issues, or suggestions:
- Email: sufyanmughal522@gmail.com
- Report issues on GitHub
- Pull requests are welcome!

## 🙏 Support

If you find this tool useful, please consider:
- Starring the repository
- Sharing it with friends
- Contributing to the code
- Reporting any bugs you find

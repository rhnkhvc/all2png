import os
import sys
import urllib.request
import zipfile
import shutil

def download_and_extract():
    target_bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
    os.makedirs(target_bin_dir, exist_ok=True)
    
    # Try a few common URLs for precompiled win64 binaries
    urls = [
        "https://github.com/LibreDWG/libredwg/releases/download/0.12.5/libredwg-0.12.5-win64.zip",
        "https://github.com/LibreDWG/libredwg/releases/download/v0.12.5/libredwg-0.12.5-win64.zip",
        "https://github.com/LibreDWG/libredwg/releases/download/0.12.4/libredwg-0.12.4-win64.zip",
        "https://github.com/LibreDWG/libredwg/releases/download/v0.12.4/libredwg-0.12.4-win64.zip"
    ]
    
    zip_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libredwg.zip")
    extract_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libredwg_temp")
    
    download_success = False
    
    for url in urls:
        print(f"Trying to download LibreDWG from: {url}...")
        try:
            # Set a user-agent to avoid being blocked by GitHub
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=30) as response, open(zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            print("Download successful!")
            download_success = True
            break
        except Exception as e:
            print(f"Failed to download from {url}: {e}")
            if os.path.exists(zip_path):
                os.remove(zip_path)

    if not download_success:
        print("Error: Failed to download LibreDWG binaries from all URLs.", file=sys.stderr)
        return False
        
    print(f"Extracting ZIP archive: {zip_path}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        print("Extraction complete!")
        
        # Locate the bin directory inside the extracted files
        bin_source = None
        for root, dirs, files in os.walk(extract_dir):
            if "dwg2dxf.exe" in files:
                bin_source = root
                break
                
        if not bin_source:
            print("Error: Could not find 'dwg2dxf.exe' inside the extracted files.", file=sys.stderr)
            return False
            
        print(f"Copying files from {bin_source} to {target_bin_dir}...")
        copied_count = 0
        for item in os.listdir(bin_source):
            s_item = os.path.join(bin_source, item)
            d_item = os.path.join(target_bin_dir, item)
            if os.path.isfile(s_item):
                shutil.copy2(s_item, d_item)
                print(f"  Copied: {item}")
                copied_count += 1
                
        print(f"Successfully configured LibreDWG! Copied {copied_count} files.")
        return True
        
    except Exception as e:
        print(f"Error during extraction/copy: {e}", file=sys.stderr)
        return False
        
    finally:
        # Clean up files
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)

if __name__ == "__main__":
    download_and_extract()

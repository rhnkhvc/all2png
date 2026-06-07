import os
import sys
import argparse
import subprocess
import shutil
import tempfile
from typing import Optional

# Import ezdxf and matplotlib if available
try:
    import ezdxf
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.properties import LayoutProperties
    import matplotlib.pyplot as plt
    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False

def find_libre_dwg_tool(tool_name: str) -> Optional[str]:
    """Finds a LibreDWG CLI tool (e.g. 'dwg2dxf' or 'dxf2dwg') in the system PATH or local directories."""
    # 1. Search in system PATH
    path = shutil.which(tool_name)
    if path:
        return path
    
    # 2. Search for Windows-specific executable in system PATH
    path = shutil.which(f"{tool_name}.exe")
    if path:
        return path
        
    # 3. Search in local bin folder
    local_bin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", f"{tool_name}.exe")
    if os.path.exists(local_bin):
        return local_bin
        
    local_bin_no_ext = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", tool_name)
    if os.path.exists(local_bin_no_ext):
        return local_bin_no_ext

    return None

def find_oda_converter() -> Optional[str]:
    """Finds ODAFileConverter.exe in standard Program Files directories."""
    possible_roots = [
        r"C:\Program Files\ODA",
        r"C:\Program Files (x86)\ODA"
    ]
    for root in possible_roots:
        if os.path.exists(root):
            for r, dirs, files in os.walk(root):
                if "ODAFileConverter.exe" in files:
                    return os.path.join(r, "ODAFileConverter.exe")
    return None

def convert_using_oda(input_path: str, output_path: str, target_format: str, version: Optional[str] = None) -> bool:
    """Invokes ODA File Converter to process a drawing using positional batch arguments."""
    oda_exe = find_oda_converter()
    if not oda_exe:
        return False
        
    print(f"ODAFileConverter found at: {oda_exe}. Using high-fidelity engine...")
    
    # Setup version string (default to 2013 for compatibility)
    ver_str = "2013"
    if version:
        ver_str = version.replace("R", "")
    
    # ODA target versions: ACAD2018, ACAD2013, ACAD2010, etc.
    if target_format.lower() == "dxf":
        oda_version = f"ACAD{ver_str}_DXF" if ver_str != "12" else "ACAD12_DXF"
    else:
        oda_version = f"ACAD{ver_str}" if ver_str != "12" else "ACAD12"
        
    with tempfile.TemporaryDirectory() as temp_dir:
        src_dir = os.path.join(temp_dir, "src")
        dest_dir = os.path.join(temp_dir, "dest")
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(dest_dir, exist_ok=True)
        
        # Copy input file to ODA source directory
        input_ext = os.path.splitext(input_path.lower())[1]
        temp_input_name = f"input{input_ext}"
        shutil.copy2(input_path, os.path.join(src_dir, temp_input_name))
        
        # Run ODA: ODAFileConverter <source_dir> <dest_dir> <filter> <version> <recursive> <audit>
        cmd = [
            oda_exe,
            src_dir,
            dest_dir,
            temp_input_name,
            oda_version,
            "0", # recursive: 0
            "0"  # audit: 0
        ]
        
        print(f"Running ODA: {' '.join(cmd)}")
        try:
            # ODA Converter prints progress and exits
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
            print("ODA stdout:", result.stdout)
            
            # Locate expected output file in dest_dir
            expected_ext = f".{target_format.lower()}"
            expected_name = f"input{expected_ext}"
            converted_file = os.path.join(dest_dir, expected_name)
            
            if os.path.exists(converted_file):
                shutil.copy2(converted_file, output_path)
                print(f"ODA conversion successful! Saved to {output_path}")
                return True
            else:
                print("Error: ODA conversion completed but expected output was not created.", file=sys.stderr)
                return False
        except Exception as e:
            print(f"Failed to execute ODA File Converter: {e}", file=sys.stderr)
            return False

def convert_dwg_to_dxf(dwg_path: str, dxf_path: str, version: Optional[str] = None) -> bool:
    """Converts a DWG file to DXF using ODA Converter if available, otherwise falls back to LibreDWG."""
    # 1. Try ODA Converter (flawless AutoCAD 2018+ support)
    if find_oda_converter():
        if convert_using_oda(dwg_path, dxf_path, "dxf", version=version):
            return True
            
    # 2. Fallback to LibreDWG (GPLv3)
    tool = find_libre_dwg_tool("dwg2dxf")
    if not tool:
        print("Error: 'dwg2dxf' (LibreDWG) was not found in PATH or 'bin' folder.", file=sys.stderr)
        print("Please install LibreDWG or place the binaries in the 'bin' folder.", file=sys.stderr)
        return False
        
    cmd = [tool, "-y", "-o", dxf_path]
    if version:
        cmd.append(f"--as={version.lower()}")
    cmd.append(dwg_path)
    
    print(f"Running Fallback LibreDWG: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        print("LibreDWG stdout:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"LibreDWG failed with exit code {e.returncode}", file=sys.stderr)
        print("Error output:", e.stderr, file=sys.stderr)
        return False
    except Exception as e:
        print(f"Failed to run LibreDWG fallback: {e}", file=sys.stderr)
        return False

def fix_dxf_for_libredwg(dxf_path: str):
    """
    Parses dxf_path line by line and replaces group code 96 with 94
    and group code 305 with 303 inside BLOCKROTATEACTION blocks to bypass 
    LibreDWG's parser bugs.
    Uses strict i % 2 == 0 check to ensure we only look at Group Codes,
    preventing values of 0 from being misparsed as entity boundary codes.
    """
    if not os.path.exists(dxf_path):
        return
        
    print(f"Applying LibreDWG compatibility patch to DXF: {dxf_path}", file=sys.stderr)
    try:
        # DXF files can be UTF-8 or other encodings
        try:
            with open(dxf_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            with open(dxf_path, 'r', encoding='cp1252', errors='ignore') as f:
                lines = f.readlines()
                
        modified = False
        in_block_rotate = False
        
        i = 0
        n = len(lines)
        while i < n:
            # Group code is ALWAYS on an even index in the line list (0-based)
            if i % 2 == 0:
                line = lines[i].strip()
                # If we see group code 0, a new entity/object starts
                if line == "0" and i + 1 < n:
                    next_line = lines[i+1].strip()
                    if next_line == "BLOCKROTATEACTION":
                        in_block_rotate = True
                        print(f"Entering BLOCKROTATEACTION at line {i+1}", file=sys.stderr)
                    else:
                        if in_block_rotate:
                            print(f"Exiting BLOCKROTATEACTION at line {i+1} due to new object {repr(next_line)}", file=sys.stderr)
                        in_block_rotate = False
                
                # If we are inside BLOCKROTATEACTION and find group code 96
                if in_block_rotate and line == "96":
                    orig_line = lines[i]
                    new_line = orig_line.replace("96", "94", 1)
                    lines[i] = new_line
                    modified = True
                    print(f"Patched DXF group code 96 -> 94 at line {i+1}: {repr(orig_line)} -> {repr(new_line)}", file=sys.stderr)
                    
                # If we are inside BLOCKROTATEACTION and find group code 305
                if in_block_rotate and line == "305":
                    orig_line = lines[i]
                    new_line = orig_line.replace("305", "303", 1)
                    lines[i] = new_line
                    modified = True
                    print(f"Patched DXF group code 305 -> 303 at line {i+1}: {repr(orig_line)} -> {repr(new_line)}", file=sys.stderr)
                    
            i += 1
            
        if modified:
            with open(dxf_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.writelines(lines)
            print("DXF compatibility patch successfully applied!", file=sys.stderr)
        else:
            print("No BLOCKROTATEACTION blocks with group codes 96 or 305 found.", file=sys.stderr)
    except Exception as e:
        print(f"Error while patching DXF: {e}", file=sys.stderr)

def convert_dxf_to_dwg(dxf_path: str, dwg_path: str, version: Optional[str] = None) -> bool:
    """Converts a DXF file to DWG using ODA Converter if available, otherwise falls back to LibreDWG."""
    # 1. Try ODA Converter (flawless AutoCAD 2018+ support)
    if find_oda_converter():
        if convert_using_oda(dxf_path, dwg_path, "dwg", version=version):
            return True
            
    # Apply LibreDWG compatibility patch to DXF
    fix_dxf_for_libredwg(dxf_path)
            
    # 2. Fallback to LibreDWG (GPLv3)
    tool = find_libre_dwg_tool("dxf2dwg")
    if not tool:
        print("Error: 'dxf2dwg' (LibreDWG) was not found in PATH or 'bin' folder.", file=sys.stderr)
        return False
        
    cmd = [tool, "-y", "-o", dwg_path]
    
    target_version = version
    if target_version:
        # LibreDWG encoder only supports up to R2000 (AC1015). Downgrade higher versions for compatibility.
        try:
            ver_num = int(target_version.upper().replace("R", ""))
            if ver_num > 2000:
                print(f"LibreDWG encoder only supports up to R2000. Automatically mapping version {target_version} to R2000 for safety.", file=sys.stderr)
                target_version = "R2000"
        except ValueError:
            pass
            
        cmd.append(f"--as={target_version.lower()}")
    cmd.append(dxf_path)
    
    print(f"Running Fallback LibreDWG: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        print("LibreDWG stdout:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"LibreDWG failed with exit code {e.returncode}", file=sys.stderr)
        print("Error output:", e.stderr, file=sys.stderr)
        return False
    except Exception as e:
        print(f"Failed to run LibreDWG fallback: {e}", file=sys.stderr)
        return False

def render_dxf_to_image(dxf_path: str, output_path: str, theme: str = "light", dpi: int = 300) -> bool:
    """Renders a DXF file to a high-resolution PNG or PDF using ezdxf and matplotlib."""
    if not HAS_EZDXF:
        print("Error: 'ezdxf' or 'matplotlib' is not installed. Rendering to image is disabled.", file=sys.stderr)
        return False
        
    try:
        print(f"Loading DXF: {dxf_path}...")
        doc = ezdxf.readfile(dxf_path)
        
        # Fix missing block definitions to prevent DXFStructureError during rendering
        referenced_blocks = set()
        try:
            for layout in doc.layouts:
                for entity in layout.query("INSERT"):
                    referenced_blocks.add(entity.dxf.name)
            for block in doc.blocks:
                for entity in block.query("INSERT"):
                    referenced_blocks.add(entity.dxf.name)
                    
            for block_name in referenced_blocks:
                if block_name not in doc.blocks:
                    print(f"Warning: Creating missing block definition for '{block_name}'", file=sys.stderr)
                    doc.blocks.new(name=block_name)
        except Exception as block_err:
            print(f"Non-critical warning while scanning referenced blocks: {block_err}", file=sys.stderr)
            
        msp = doc.modelspace()
        
        print("Preparing rendering context...")
        ctx = RenderContext(doc)
        
        # Apply theme colors using LayoutProperties
        bg_color = "#ffffff" if theme == "light" else "#121212"
        fg_color = "#000000" if theme == "light" else "#ffffff"
        
        msp_properties = LayoutProperties.from_layout(msp)
        msp_properties.set_colors(bg_color)
        
        # Setup Matplotlib figure
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_facecolor(bg_color)
        
        # Render using ezdxf frontend
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(msp, layout_properties=msp_properties, finalize=True)
        
        # Save output
        print(f"Saving rendered image to: {output_path}...")
        fig.savefig(output_path, dpi=dpi, facecolor=bg_color, edgecolor='none', bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        print("Rendering completed successfully!")
        return True
    except Exception as e:
        print(f"Error during rendering: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(
        description="CAD-Converter: Legally-safe DWG/DXF converter and PNG/PDF renderer prototype.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Render DXF to a high-res light-themed PNG
  python converter.py --input drawing.dxf --output drawing.png --theme light
  
  # Render DXF to dark-themed PNG
  python converter.py --input drawing.dxf --output drawing.png --theme dark --dpi 450

  # Convert DWG to DXF (Requires LibreDWG)
  python converter.py --input drawing.dwg --output drawing.dxf

  # Convert DWG to older DXF version (e.g. R2010) (Requires LibreDWG)
  python converter.py --input drawing.dwg --output drawing_r2010.dxf --version R2010
"""
    )
    parser.add_argument("-i", "--input", required=True, help="Path to input CAD file (.dwg or .dxf)")
    parser.add_argument("-o", "--output", required=True, help="Path to output file (.dwg, .dxf, .png, .pdf)")
    parser.add_argument("-v", "--version", choices=["R12", "R14", "R2000", "R2004", "R2007", "R2010", "R2013", "R2018"], 
                        help="Target CAD version (Only applicable when converting between CAD formats)")
    parser.add_argument("-t", "--theme", choices=["light", "dark"], default="light", help="Theme for PNG/PDF rendering (default: light)")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for PNG rendering (default: 300)")
    
    args = parser.parse_args()
    
    input_ext = os.path.splitext(args.input.lower())[1]
    output_ext = os.path.splitext(args.output.lower())[1]
    
    if input_ext not in [".dwg", ".dxf"]:
        print(f"Error: Unsupported input file extension '{input_ext}'. Must be .dwg or .dxf", file=sys.stderr)
        sys.exit(1)
        
    if output_ext not in [".dwg", ".dxf", ".png", ".pdf"]:
        print(f"Error: Unsupported output file extension '{output_ext}'. Must be .dwg, .dxf, .png, or .pdf", file=sys.stderr)
        sys.exit(1)

    # Temporary directory to handle intermediate file operations if needed
    with tempfile.TemporaryDirectory() as temp_dir:
        
        # CASE 1: Render CAD to Image (PNG / PDF)
        if output_ext in [".png", ".pdf"]:
            dxf_for_render = args.input
            
            # If input is DWG, we must convert it to DXF first
            if input_ext == ".dwg":
                dxf_for_render = os.path.join(temp_dir, "temp_render.dxf")
                print(f"Input is DWG. Converting to intermediate DXF for rendering...")
                success = convert_dwg_to_dxf(args.input, dxf_for_render)
                if not success:
                    print("Error: DWG to intermediate DXF conversion failed. Cannot render image.", file=sys.stderr)
                    sys.exit(1)
                    
            # Render the DXF to image
            success = render_dxf_to_image(dxf_for_render, args.output, theme=args.theme, dpi=args.dpi)
            if not success:
                sys.exit(1)
                
        # CASE 2: CAD to CAD Conversion
        else:
            print(f"Performing CAD-to-CAD conversion from {input_ext} to {output_ext}...")
            
            # Subcase A: DWG to DXF
            if input_ext == ".dwg" and output_ext == ".dxf":
                success = convert_dwg_to_dxf(args.input, args.output, version=args.version)
                if not success:
                    sys.exit(1)
                    
            # Subcase B: DXF to DWG
            elif input_ext == ".dxf" and output_ext == ".dwg":
                success = convert_dxf_to_dwg(args.input, args.output, version=args.version)
                if not success:
                    sys.exit(1)
                    
            # Subcase C: DWG to DWG (e.g. Version Change)
            elif input_ext == ".dwg" and output_ext == ".dwg":
                temp_dxf = os.path.join(temp_dir, "temp_dwg_conv.dxf")
                print("Step 1: Converting DWG to intermediate DXF...")
                if not convert_dwg_to_dxf(args.input, temp_dxf):
                    sys.exit(1)
                print("Step 2: Converting intermediate DXF to output DWG with target version...")
                if not convert_dxf_to_dwg(temp_dxf, args.output, version=args.version):
                    sys.exit(1)
                    
            # Subcase D: DXF to DXF (e.g. Version Change)
            elif input_ext == ".dxf" and output_ext == ".dxf":
                temp_dwg = os.path.join(temp_dir, "temp_dxf_conv.dwg")
                print("Step 1: Converting DXF to intermediate DWG...")
                if not convert_dxf_to_dwg(args.input, temp_dwg):
                    sys.exit(1)
                print("Step 2: Converting intermediate DWG to output DXF with target version...")
                if not convert_dwg_to_dxf(temp_dwg, args.output, version=args.version):
                    sys.exit(1)
                    
    print(f"Success! Saved output to: {args.output}")

if __name__ == "__main__":
    main()

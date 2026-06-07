import os
import sys
import uuid
import tempfile
import shutil
from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS

# Import the CAD conversion engine functions from converter.py
from converter import convert_dwg_to_dxf, convert_dxf_to_dwg, render_dxf_to_image

app = Flask(__name__)
CORS(app) # Allow CORS for frontend interaction

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "free-converter-web"))

# Route to serve the main frontend static pages
@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:filename>")
def serve_static(filename):
    # Ensure file exists in frontend directory before serving
    if os.path.exists(os.path.join(FRONTEND_DIR, filename)):
        return send_from_directory(FRONTEND_DIR, filename)
    else:
        return jsonify({"error": "File not found"}), 404

# Core API Endpoint for CAD conversions
@app.route("/api/convert", methods=["POST"])
def api_convert():
    # 1. Validation
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    uploaded_file = request.files["file"]
    if uploaded_file.filename == "":
        return jsonify({"error": "No file selected"}), 400
        
    output_format = request.form.get("format", "png").lower()
    version = request.form.get("version", None)
    theme = request.form.get("theme", "light")
    
    try:
        dpi = int(request.form.get("dpi", 300))
    except ValueError:
        dpi = 300
        
    if output_format not in ["png", "pdf", "dxf", "dwg"]:
        return jsonify({"error": "Unsupported output format"}), 400

    # 2. Temporary Working Directory (GDPR/KVKK Garbage Collection compliant)
    temp_working_dir = tempfile.mkdtemp()
    
    try:
        # Save uploaded file inside secure temporary directory
        input_filename = f"uploaded_{uuid.uuid4().hex}{os.path.splitext(uploaded_file.filename)[1]}"
        input_path = os.path.join(temp_working_dir, input_filename)
        uploaded_file.save(input_path)
        
        input_ext = os.path.splitext(uploaded_file.filename.lower())[1]
        
        if input_ext not in [".dwg", ".dxf"]:
            return jsonify({"error": "Only .dwg or .dxf files are supported as input"}), 400
            
        output_filename = f"converted_{uuid.uuid4().hex}.{output_format}"
        output_path = os.path.join(temp_working_dir, output_filename)
        
        # 3. Handle Conversions
        
        # CASE 1: Render CAD to Image (PNG / PDF)
        if output_format in ["png", "pdf"]:
            dxf_path = input_path
            
            # Convert DWG to DXF intermediate if needed
            if input_ext == ".dwg":
                dxf_path = os.path.join(temp_working_dir, "temp_render.dxf")
                success = convert_dwg_to_dxf(input_path, dxf_path)
                if not success:
                    return jsonify({"error": "Failed to parse DWG input file."}), 500
                    
            success = render_dxf_to_image(dxf_path, output_path, theme=theme, dpi=dpi)
            if not success:
                return jsonify({"error": "Failed to render CAD to image."}), 500
                
        # CASE 2: CAD to CAD Conversion
        else:
            # Subcase A: DWG to DXF
            if input_ext == ".dwg" and output_format == "dxf":
                success = convert_dwg_to_dxf(input_path, output_path, version=version)
                if not success:
                    return jsonify({"error": "Failed to convert DWG to DXF."}), 500
                    
            # Subcase B: DXF to DWG
            elif input_ext == ".dxf" and output_format == "dwg":
                success = convert_dxf_to_dwg(input_path, output_path, version=version)
                if not success:
                    return jsonify({"error": "Failed to convert DXF to DWG."}), 500
                    
            # Subcase C: DWG to DWG (e.g. Version Change)
            elif input_ext == ".dwg" and output_format == "dwg":
                temp_dxf = os.path.join(temp_working_dir, "temp_conv.dxf")
                if not convert_dwg_to_dxf(input_path, temp_dxf):
                    return jsonify({"error": "Failed to parse source DWG."}), 500
                if not convert_dxf_to_dwg(temp_dxf, output_path, version=version):
                    return jsonify({"error": "Failed to write target DWG version."}), 500
                    
            # Subcase D: DXF to DXF (e.g. Version Change)
            elif input_ext == ".dxf" and output_format == "dxf":
                temp_dwg = os.path.join(temp_working_dir, "temp_conv.dwg")
                if not convert_dxf_to_dwg(input_path, temp_dwg):
                    return jsonify({"error": "Failed to parse source DXF."}), 500
                if not convert_dwg_to_dxf(temp_dwg, output_path, version=version):
                    return jsonify({"error": "Failed to write target DXF version."}), 500

        # Send back the converted file as an attachment
        friendly_basename = os.path.splitext(uploaded_file.filename)[0]
        friendly_output_name = f"{friendly_basename}_converted.{output_format}"
        
        # Load converted file into memory (RAM BytesIO) before deleting temporary directory (GDPR compliant)
        import io
        with open(output_path, "rb") as f:
            file_bytes = io.BytesIO(f.read())
            
        return send_file(
            file_bytes,
            as_attachment=True,
            download_name=friendly_output_name,
            mimetype="application/octet-stream"
        )

    except Exception as e:
        print(f"Server Error during conversion: {e}", file=sys.stderr)
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500
        
    finally:
        # 4. PHYSICAL CLEANUP of uploaded and processed files immediately (GDPR/KVKK compliant)
        try:
            shutil.rmtree(temp_working_dir)
            print(f"Cleaned up temp workspace: {temp_working_dir}")
        except Exception as e:
            print(f"Failed to delete temp dir {temp_working_dir}: {e}", file=sys.stderr)

if __name__ == "__main__":
    print(f"Starting CAD Converter full-stack server...")
    print(f"Serving frontend from: {FRONTEND_DIR}")
    app.run(host="127.0.0.1", port=5000, debug=False)

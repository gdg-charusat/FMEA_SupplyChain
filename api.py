"""
REST API for FMEA Generator
Test with Postman
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yaml
import sys
from pathlib import Path
import pandas as pd
import tempfile
import os

sys.path.append(str(Path(__file__).parent / 'src'))

from fmea_generator import FMEAGenerator

app = Flask(__name__)
CORS(app)

# Load config
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

generator = FMEAGenerator(config)

# Resource limits
MAX_FILE_SIZE_MB = 50
MAX_TEXT_ENTRIES = 1000

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "FMEA Generator API"}), 200

@app.route('/api/fmea/text', methods=['POST'])
def generate_from_text():
    """
    Generate FMEA from unstructured text
    
    Body (JSON):
    {
        "texts": ["failure description 1", "failure description 2"]
    }
    """
    try:
        data = request.get_json()
        texts = data.get('texts', [])
        
        if not texts:
            return jsonify({"error": "No texts provided"}), 400
        
        if len(texts) > MAX_TEXT_ENTRIES:
            return jsonify({"error": f"Too many entries. Max: {MAX_TEXT_ENTRIES}"}), 400
        
        fmea_df = generator.generate_from_text(texts, is_file=False)
        
        return jsonify({
            "status": "success",
            "count": len(fmea_df),
            "data": fmea_df.to_dict(orient='records')
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/fmea/file', methods=['POST'])
def generate_from_file():
    """
    Generate FMEA from CSV/Excel file
    
    Form Data:
    - file: CSV or Excel file
    - type: "structured" or "unstructured"
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        file_type = request.form.get('type', 'structured')
        
        # Validate file size
        file.seek(0, os.SEEK_END)
        file_size_mb = file.tell() / (1024 * 1024)
        file.seek(0)
        
        if file_size_mb > MAX_FILE_SIZE_MB:
            return jsonify({"error": f"File too large. Max: {MAX_FILE_SIZE_MB} MB"}), 400
        
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            if file_type == 'structured':
                fmea_df = generator.generate_from_structured(tmp_path)
            else:
                fmea_df = generator.generate_from_text(tmp_path, is_file=True)
            
            return jsonify({
                "status": "success",
                "count": len(fmea_df),
                "data": fmea_df.to_dict(orient='records')
            }), 200
            
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/fmea/hybrid', methods=['POST'])
def generate_hybrid():
    """
    Generate FMEA from both structured file and text
    
    Form Data:
    - file: CSV/Excel file (optional)
    - texts: JSON array of text strings (optional)
    """
    try:
        structured_path = None
        texts = None
        
        # Handle file
        if 'file' in request.files:
            file = request.files['file']
            file.seek(0, os.SEEK_END)
            file_size_mb = file.tell() / (1024 * 1024)
            file.seek(0)
            
            if file_size_mb > MAX_FILE_SIZE_MB:
                return jsonify({"error": f"File too large. Max: {MAX_FILE_SIZE_MB} MB"}), 400
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
                file.save(tmp.name)
                structured_path = tmp.name
        
        # Handle texts
        if request.form.get('texts'):
            import json
            texts = json.loads(request.form.get('texts'))
            if len(texts) > MAX_TEXT_ENTRIES:
                return jsonify({"error": f"Too many text entries. Max: {MAX_TEXT_ENTRIES}"}), 400
        
        if not structured_path and not texts:
            return jsonify({"error": "Provide either file or texts"}), 400
        
        try:
            fmea_df = generator.generate_hybrid(
                structured_file=structured_path,
                text_input=texts
            )
            
            return jsonify({
                "status": "success",
                "count": len(fmea_df),
                "data": fmea_df.to_dict(orient='records')
            }), 200
            
        finally:
            if structured_path:
                Path(structured_path).unlink(missing_ok=True)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/fmea/export', methods=['POST'])
def export_fmea():
    """
    Export FMEA data to Excel/CSV
    
    Body (JSON):
    {
        "data": [...],  // FMEA records
        "format": "excel" or "csv"
    }
    """
    try:
        data = request.get_json()
        records = data.get('data', [])
        format_type = data.get('format', 'excel')
        
        if not records:
            return jsonify({"error": "No data provided"}), 400
        
        df = pd.DataFrame(records)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_type}') as tmp:
            if format_type == 'excel':
                generator.export_fmea(df, tmp.name, format='excel')
                mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            else:
                generator.export_fmea(df, tmp.name, format='csv')
                mimetype = 'text/csv'
            
            return send_file(
                tmp.name,
                mimetype=mimetype,
                as_attachment=True,
                download_name=f'fmea_export.{format_type}'
            )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['POST'])
def get_statistics():
    """
    Get statistics from FMEA data
    
    Body (JSON):
    {
        "data": [...]  // FMEA records
    }
    """
    try:
        data = request.get_json()
        records = data.get('data', [])
        
        if not records:
            return jsonify({"error": "No data provided"}), 400
        
        df = pd.DataFrame(records)
        
        stats = {
            "total_failures": len(df),
            "critical_count": len(df[df['Action Priority'] == 'Critical']),
            "high_count": len(df[df['Action Priority'] == 'High']),
            "medium_count": len(df[df['Action Priority'] == 'Medium']),
            "low_count": len(df[df['Action Priority'] == 'Low']),
            "avg_rpn": float(df['Rpn'].mean()),
            "max_rpn": int(df['Rpn'].max()),
            "min_rpn": int(df['Rpn'].min()),
            "avg_severity": float(df['Severity'].mean()),
            "avg_occurrence": float(df['Occurrence'].mean()),
            "avg_detection": float(df['Detection'].mean())
        }
        
        return jsonify({"status": "success", "statistics": stats}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("FMEA Generator API Server")
    print("="*60)
    print("\nEndpoints:")
    print("  GET  /health              - Health check")
    print("  POST /api/fmea/text       - Generate from text")
    print("  POST /api/fmea/file       - Generate from file")
    print("  POST /api/fmea/hybrid     - Generate hybrid")
    print("  POST /api/fmea/export     - Export FMEA")
    print("  POST /api/stats           - Get statistics")
    print("\nServer running on: http://localhost:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

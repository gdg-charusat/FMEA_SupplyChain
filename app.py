"""
Streamlit Dashboard for FMEA Generator
Interactive web interface for generating and analyzing FMEA
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import yaml
import sys
import os
from datetime import datetime
import logging
from PIL import Image
import io

# Add src directory to path
sys.path.append(str(Path(__file__).parent / 'src'))

from fmea_generator import FMEAGenerator
from preprocessing import DataPreprocessor
from llm_extractor import LLMExtractor
from risk_scoring import RiskScoringEngine
from ocr_processor import OCRProcessor
from history_tracker import FMEAHistoryTracker
from voice_input import VoiceInputProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Resource limits to prevent DoS attacks
MAX_FILE_UPLOAD_SIZE_MB = 50
MAX_TEXT_INPUT_LENGTH = 50000
MAX_BATCH_PROCESSING = 5000

# Currency conversion rate (USD to INR)
USD_TO_INR_RATE = 83.50

def format_currency(amount, currency='USD'):
    """
    Format currency based on type (USD or INR).
    
    Args:
        amount: Numeric amount to format
        currency: 'USD' or 'INR'
    
    Returns:
        Formatted string like "$10,000.00" or "₹8,35,000.00"
    """
    if amount is None:
        return "N/A"
    
    if currency == 'INR':
        return f"₹{amount:,.2f}"
    else:
        return f"${amount:,.2f}"

def get_currency_symbol(currency='USD'):
    """Get currency symbol."""
    return "₹" if currency == 'INR' else "$"

def validate_file_upload(uploaded_file) -> tuple:
    """Validate file upload size and type"""
    if uploaded_file is None:
        return False, "No file uploaded"
    
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    if file_size_mb > MAX_FILE_UPLOAD_SIZE_MB:
        return False, f"File size ({file_size_mb:.1f} MB) exceeds maximum allowed size ({MAX_FILE_UPLOAD_SIZE_MB} MB)"
    
    allowed_extensions = ['.csv', '.xlsx', '.xls', '.png', '.jpg', '.jpeg', '.pdf']
    file_ext = '.' + uploaded_file.name.split('.')[-1].lower()
    if file_ext not in allowed_extensions:
        return False, f"File type {file_ext} not allowed. Allowed: {', '.join(allowed_extensions)}"
    
    return True, "Valid"

def validate_text_input(text: str) -> tuple:
    """Validate text input length"""
    if not text or not text.strip():
        return False, "Text input is empty"
    
    if len(text) > MAX_TEXT_INPUT_LENGTH:
        return False, f"Text length ({len(text)} chars) exceeds maximum allowed ({MAX_TEXT_INPUT_LENGTH} chars)"
    
    return True, "Valid"

# Page configuration
st.set_page_config(
    page_title="LLM-Powered FMEA Generator",
    page_icon="⚠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #ff7f0e;
        margin-top: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .stDataFrame {
        border: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_config():
    """Load configuration from YAML file with security validation"""
    from config_validator import load_config_safe
    
    config_path = Path('config/config.yaml')
    if config_path.exists():
        try:
            return load_config_safe(str(config_path))
        except ValueError as e:
            st.error(f"Configuration validation failed: {e}")
            return {}
    else:
        st.error("Configuration file not found!")
        return {}


@st.cache_resource
def initialize_generator(_config):
    """Initialize FMEA Generator (cached to avoid reloading model)"""
    return FMEAGenerator(_config)


def display_metrics(fmea_df):
    """Display key metrics from FMEA"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Failure Modes",
            value=len(fmea_df)
        )
    
    with col2:
        critical_count = len(fmea_df[fmea_df['Action Priority'] == 'Critical'])
        st.metric(
            label="Critical Issues",
            value=critical_count,
            delta="Needs Immediate Action" if critical_count > 0 else None
        )
    
    with col3:
        avg_rpn = fmea_df['Rpn'].mean()
        st.metric(
            label="Average RPN",
            value=f"{avg_rpn:.1f}"
        )
    
    with col4:
        max_rpn = fmea_df['Rpn'].max()
        st.metric(
            label="Maximum RPN",
            value=int(max_rpn)
        )


def plot_rpn_distribution(fmea_df):
    """Plot RPN distribution"""
    fig = px.histogram(
        fmea_df,
        x='Rpn',
        nbins=30,
        title='RPN Distribution',
        labels={'Rpn': 'Risk Priority Number', 'count': 'Frequency'},
        color_discrete_sequence=['#1f77b4']
    )
    fig.update_layout(showlegend=False)
    return fig


def plot_priority_distribution(fmea_df):
    """Plot action priority distribution"""
    priority_counts = fmea_df['Action Priority'].value_counts()
    
    colors = {
        'Critical': '#d62728',
        'High': '#ff7f0e',
        'Medium': '#ffbb78',
        'Low': '#2ca02c'
    }
    
    fig = go.Figure(data=[
        go.Pie(
            labels=priority_counts.index,
            values=priority_counts.values,
            marker=dict(colors=[colors.get(p, '#1f77b4') for p in priority_counts.index])
        )
    ])
    fig.update_layout(title='Action Priority Distribution')
    return fig


def plot_risk_matrix(fmea_df):
    """Plot risk matrix (Severity vs Occurrence)"""
    fig = px.scatter(
        fmea_df,
        x='Occurrence',
        y='Severity',
        size='Rpn',
        color='Action Priority',
        hover_data=['Failure Mode', 'Effect'],
        title='Risk Matrix (Severity vs Occurrence)',
        color_discrete_map={
            'Critical': '#d62728',
            'High': '#ff7f0e',
            'Medium': '#ffbb78',
            'Low': '#2ca02c'
        }
    )
    fig.update_xaxes(range=[0, 11])
    fig.update_yaxes(range=[0, 11])
    return fig


def plot_top_risks(fmea_df, top_n=10):
    """Plot top N risks by RPN"""
    top_risks = fmea_df.nlargest(top_n, 'Rpn')
    
    fig = px.bar(
        top_risks,
        x='Rpn',
        y='Failure Mode',
        orientation='h',
        title=f'Top {top_n} Risks by RPN',
        color='Action Priority',
        color_discrete_map={
            'Critical': '#d62728',
            'High': '#ff7f0e',
            'Medium': '#ffbb78',
            'Low': '#2ca02c'
        }
    )
    fig.update_yaxes(autorange="reversed")
    return fig


def extract_text_from_image(image_file):
    """Extract text from image using OCR"""
    try:
        # Try EasyOCR first (no external dependencies needed)
        try:
            import easyocr
            from PIL import Image as PILImage
            
            # Create reader (cached for performance)
            if 'easyocr_reader' not in st.session_state:
                with st.spinner("Initializing OCR engine (first time only)..."):
                    st.session_state.easyocr_reader = easyocr.Reader(['en'], gpu=False)
            
            reader = st.session_state.easyocr_reader
            
            # Save image temporarily
            img = PILImage.open(image_file)
            temp_img_path = "temp_ocr_image.png"
            img.save(temp_img_path)
            
            # Extract text
            results = reader.readtext(temp_img_path)
            text = '\n'.join([result[1] for result in results])
            
            # Clean up
            Path(temp_img_path).unlink(missing_ok=True)
            
            return text if text.strip() else "No text found in image"
            
        except ImportError:
            # Fallback to pytesseract if easyocr not available
            try:
                import pytesseract
                from PIL import Image as PILImage
                
                # Open image
                img = PILImage.open(image_file)
                
                # Extract text
                text = pytesseract.image_to_string(img)
                
                if text.strip():
                    return text
                else:
                    return "No text found in image"
                    
            except Exception as e:
                return f"OCR libraries not properly configured. Error: {str(e)}\n\nPlease install: pip install easyocr"
                
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"Error extracting text from image: {str(e)}\n\nDetails: {error_details}"


def render_pdf_preview(pdf_bytes):
    """Render the first page of a PDF as an image for preview."""
    try:
        import fitz
        from PIL import Image as PILImage

        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            if doc.page_count == 0:
                return None
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=150, colorspace=fitz.csRGB)
            return PILImage.frombytes("RGB", (pix.width, pix.height), pix.samples)
    except Exception:
        return None


def main():
    """Main application"""
    
    # Header
    st.markdown('<div class="main-header">⚠️ LLM-Powered FMEA Generator</div>', 
                unsafe_allow_html=True)
    st.markdown("### Automated Failure Mode and Effects Analysis from Structured & Unstructured Data")
    
    # Load configuration
    config = load_config()
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/300x100/1f77b4/ffffff?text=FMEA+Generator", 
                use_column_width=True)
        st.markdown("---")
        
        st.markdown("### 📊 Input Options")
        input_type = st.radio(
            "Select Input Type:",
            ["Unstructured Text", "Structured File (CSV/Excel)", "Hybrid (Both)", "📷 Scan Document (OCR)", "🎙️ Voice Input"]
        )
        
        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        
        # Model selection
        model_options = [
            "mistralai/Mistral-7B-Instruct-v0.2",
            "meta-llama/Llama-2-7b-chat-hf",
            "Rule-based (No LLM)"
        ]
        selected_model = st.selectbox("Model Selection:", model_options)
        
        if selected_model == "Rule-based (No LLM)":
            config['model']['name'] = None
        else:
            config['model']['name'] = selected_model
        
        # Output format
        output_format = st.selectbox("Export Format:", ["Excel", "CSV"])
        
        # Whisper model size (shown when Voice Input selected)
        if input_type == "🎙️ Voice Input":
            st.markdown("---")
            st.markdown("### 🎙️ Voice Settings")
            whisper_model_size = st.selectbox(
                "Whisper Model Size:",
                ["tiny (~39 MB)", "base (~140 MB)", "small (~461 MB)", "medium (~1.5 GB)"],
                index=1
            )
            # Extract just the model name
            st.session_state['whisper_model_size'] = whisper_model_size.split(" ")[0]
        
        st.markdown("---")
        st.markdown("### 📖 About")
        st.info("""
        This system uses LLMs to automatically generate FMEA from:
        - Customer reviews
        - Complaint reports
        - Structured failure data
        
        **Features:**
        - Intelligent extraction
        - Automated risk scoring
        - Visual analytics
        - Export capabilities
        """)
    
    # Main content area
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📝 Generate FMEA", 
        "🎯 PFMEA Generator", 
        "🚚 Supply Chain Risk",
        "🔄 Model Comparison",
        "📊 Analytics", 
        "🔍 Disagreement Heatmap",
        "📈 History & Trends",
        "ℹ️ Help"
    ])
    
    with tab1:
        st.markdown('<div class="sub-header">Generate FMEA</div>', unsafe_allow_html=True)
        
        if input_type == "Unstructured Text":
            text_input_method = st.radio(
                "Input Method:",
                ["Upload File", "Enter Text Manually"]
            )
            
            if text_input_method == "Upload File":
                uploaded_file = st.file_uploader(
                    "Upload image file (PNG, JPEG) - OCR will extract text",
                    type=['png', 'jpg', 'jpeg']
                )
                
                if uploaded_file:
                    # Display uploaded image
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
                    
                    with col2:
                        if st.button("🚀 Extract Text & Generate FMEA", type="primary"):
                            with st.spinner("Extracting text from image..."):
                                # Extract text using OCR
                                extracted_text = extract_text_from_image(uploaded_file)
                                
                                # Show extracted text
                                st.markdown("**Extracted Text:**")
                                st.text_area("", extracted_text, height=150, key="extracted", disabled=True)
                                
                                if "Error" not in extracted_text and "No text found" not in extracted_text:
                                    with st.spinner("Generating FMEA from extracted text..."):
                                        generator = initialize_generator(config)
                                        # Split text into lines
                                        texts = [line.strip() for line in extracted_text.split('\n') if line.strip()]
                                        fmea_df = generator.generate_from_text(texts, is_file=False)
                                        st.session_state['fmea_df'] = fmea_df
                                        st.session_state['fmea_saved'] = False
                                else:
                                    st.error(extracted_text)
            else:
                text_input = st.text_area(
                    "Enter text (reviews, reports, complaints):",
                    height=200,
                    placeholder="Paste customer reviews, failure reports, or complaint text here..."
                )
                
                if text_input and st.button("🚀 Generate FMEA", type="primary"):
                    with st.spinner("Analyzing text and generating FMEA..."):
                        generator = initialize_generator(config)
                        texts = [line.strip() for line in text_input.split('\n') if line.strip()]
                        fmea_df = generator.generate_from_text(texts, is_file=False)
                        st.session_state['fmea_df'] = fmea_df
                        st.session_state['fmea_saved'] = False

        elif input_type == "📷 Scan Document (OCR)":
            st.markdown("**Upload an image or PDF for OCR extraction:**")
            uploaded_ocr_file = st.file_uploader(
                "Upload JPG, JPEG, PNG, or PDF",
                type=['jpg', 'jpeg', 'png', 'pdf'],
                key='ocr_upload'
            )

            if uploaded_ocr_file:
                file_bytes = uploaded_ocr_file.getvalue()
                file_name = uploaded_ocr_file.name.lower()
                file_key = f"ocr_{uploaded_ocr_file.name}_{len(file_bytes)}_{uploaded_ocr_file.type}"

                if st.session_state.get('ocr_source_key') != file_key:
                    with st.spinner("Extracting text from document..."):
                        try:
                            processor = OCRProcessor()
                            if file_name.endswith('.pdf'):
                                extracted_text = processor.extract_text_from_pdf(file_bytes)
                            else:
                                extracted_text = processor.extract_text_from_image(file_bytes)

                            st.session_state['ocr_source_key'] = file_key
                            st.session_state['ocr_text'] = extracted_text
                            st.session_state['ocr_edit'] = extracted_text
                        except Exception as e:
                            st.session_state['ocr_text'] = ""
                            st.session_state['ocr_edit'] = ""
                            st.error(f"OCR failed: {e}")

                col1, col2 = st.columns([1, 1])

                with col1:
                    if file_name.endswith('.pdf'):
                        preview_image = render_pdf_preview(file_bytes)
                        if preview_image:
                            st.image(preview_image, caption="PDF Preview", use_column_width=True)
                        else:
                            st.info("PDF uploaded. Preview not available.")
                    else:
                        st.image(uploaded_ocr_file, caption="Uploaded Image", use_column_width=True)

                with col2:
                    st.text_area(
                        "Extracted Text (editable):",
                        height=300,
                        key='ocr_edit'
                    )

                if st.button("🚀 Generate FMEA", type="primary"):
                    edited_text = st.session_state.get('ocr_edit', '').strip()
                    if not edited_text:
                        st.warning("Please review or add text before generating FMEA.")
                    else:
                        with st.spinner("Generating FMEA from OCR text..."):
                            generator = initialize_generator(config)
                            texts = [line.strip() for line in edited_text.split('\n') if line.strip()]
                            fmea_df = generator.generate_from_text(texts, is_file=False)
                            st.session_state['fmea_df'] = fmea_df
                            st.session_state['fmea_saved'] = False
        
        elif input_type == "🎙️ Voice Input":
            st.markdown("**🎙️ Record your failure description:**")
            st.info("Click the microphone button below, speak your failure description clearly, then click stop.")

            try:
                from audio_recorder_streamlit import audio_recorder
                audio_bytes = audio_recorder(
                    text="Click to record",
                    recording_color="#e74c3c",
                    neutral_color="#1f77b4",
                    pause_threshold=3.0
                )
            except ImportError:
                st.error("Audio recorder component not installed. Run: pip install audio-recorder-streamlit")
                audio_bytes = None

            if audio_bytes:
                # Show audio playback
                st.audio(audio_bytes, format="audio/wav")

                # Transcribe with Whisper
                whisper_size = st.session_state.get('whisper_model_size', 'base')
                with st.spinner(f"Transcribing audio with Whisper ({whisper_size} model)..."):
                    try:
                        processor = VoiceInputProcessor(model_size=whisper_size)
                        transcribed_text = processor.transcribe(audio_bytes)
                    except Exception as e:
                        st.error(f"Transcription failed: {e}")
                        transcribed_text = ""

                # Validate transcription
                validation = processor.validate_transcription(transcribed_text)

                if validation["valid"]:
                    edited_text = st.text_area(
                        "Review and correct transcription before generating FMEA:",
                        value=transcribed_text,
                        height=150,
                        key="voice_transcription"
                    )

                    if st.button("🚀 Generate FMEA from Voice Input", type="primary"):
                        with st.spinner("Generating FMEA from voice input..."):
                            generator = initialize_generator(config)
                            texts = [line.strip() for line in edited_text.split('\n') if line.strip()]
                            fmea_df = generator.generate_from_text(texts, is_file=False)
                            st.session_state['fmea_df'] = fmea_df
                else:
                    st.error(f"⚠️ {validation['reason']}")
                    st.warning("Please record again with a clear, longer description.")

        elif input_type == "Structured File (CSV/Excel)":
            uploaded_file = st.file_uploader(
                "Upload structured FMEA file (CSV or Excel)",
                type=['csv', 'xlsx', 'xls']
            )
            
            if uploaded_file:
                temp_path = Path(f"temp_{uploaded_file.name}")
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                if st.button("🚀 Generate FMEA", type="primary"):
                    with st.spinner("Processing structured data..."):
                        generator = initialize_generator(config)
                        fmea_df = generator.generate_from_structured(str(temp_path))
                        st.session_state['fmea_df'] = fmea_df
                        st.session_state['fmea_saved'] = False
                    
                    temp_path.unlink()
        
        else:  # Hybrid
            st.markdown("**Upload both structured and unstructured data:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Structured Data:**")
                structured_file = st.file_uploader(
                    "Upload CSV/Excel",
                    type=['csv', 'xlsx', 'xls'],
                    key='structured'
                )
            
            with col2:
                st.markdown("**Unstructured Data:**")
                unstructured_text = st.text_area(
                    "Enter text manually (reviews, reports, complaints):",
                    height=200,
                    placeholder="Paste customer reviews, failure reports, or complaint text here...",
                    key='hybrid_text'
                )
            
            generate_hybrid_btn = st.button("🚀 Generate Hybrid FMEA", type="primary")
            if generate_hybrid_btn:
                # Validate that at least one valid input is provided
                has_valid_file = False
                has_valid_text = False

                if structured_file:
                    try:
                        file_ext = structured_file.name.split('.')[-1].lower()
                        if file_ext == 'csv':
                            check_df = pd.read_csv(structured_file)
                        else:
                            check_df = pd.read_excel(structured_file)
                        structured_file.seek(0)
                        
                        if check_df.empty or len(check_df) == 0:
                            st.error("⚠️ The uploaded structured file contains no data rows.")
                            st.stop()
                        has_valid_file = True
                    except Exception as e:
                        st.error(f"⚠️ Unable to read the structured file. Error: {e}")
                        st.stop()
                
                if unstructured_text and unstructured_text.strip():
                    has_valid_text = True
                
                if not has_valid_file and not has_valid_text:
                    st.error("⚠️ Please provide at least one input: upload a structured file OR enter text manually.")
                    st.stop()

                with st.spinner("Processing hybrid data..."):
                    try:
                        generator = initialize_generator(config)
                        
                        structured_path = None
                        text_data = None
                        
                        if has_valid_file:
                            structured_path = Path(f"temp_structured_{structured_file.name}")
                            with open(structured_path, "wb") as f:
                                f.write(structured_file.getbuffer())
                        
                        if has_valid_text:
                            text_data = [line.strip() for line in unstructured_text.split('\n') if line.strip()]
                        
                        fmea_df = generator.generate_hybrid(
                            structured_file=str(structured_path) if structured_path else None,
                            text_input=text_data if text_data else None
                        )
                        st.session_state['fmea_df'] = fmea_df
                        st.session_state['fmea_saved'] = False
                        
                        # Cleanup
                        if structured_path:
                            structured_path.unlink(missing_ok=True)
                    except ValueError as e:
                        st.error(f"❌ {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Error processing hybrid data: {str(e)}")
        
        # Display results
        if 'fmea_df' in st.session_state:
            st.success("✅ FMEA Generated Successfully!")
            
            # Auto-save the run (only once per generation to avoid duplicate saves on rerun)
            if not st.session_state.get('fmea_saved', False):
                tracker = FMEAHistoryTracker("history")
                run_id = tracker.save_run(st.session_state['fmea_df'], label=f"Run {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                st.caption(f"💾 Run saved (ID: {run_id})")
                st.session_state['fmea_saved'] = True
            
            fmea_df = st.session_state['fmea_df']
            
            # Display metrics
            st.markdown("---")
            st.markdown("### 📈 Key Metrics")
            display_metrics(fmea_df)
            
            # Display FMEA table
            st.markdown("---")
            st.markdown("### 📋 FMEA Table")
            
            # Add filtering options
            col1, col2 = st.columns(2)
            with col1:
                priority_filter = st.multiselect(
                    "Filter by Priority:",
                    options=['Critical', 'High', 'Medium', 'Low'],
                    default=['Critical', 'High', 'Medium', 'Low']
                )
            
            with col2:
                rpn_threshold = st.slider("Minimum RPN:", 0, 1000, 0)
            
            filtered_df = fmea_df[
                (fmea_df['Action Priority'].isin(priority_filter)) &
                (fmea_df['Rpn'] >= rpn_threshold)
            ]
            
            st.dataframe(filtered_df, use_container_width=True, height=400)
            
            # Export options
            st.markdown("---")
            st.markdown("### 💾 Export FMEA")
            
            col1, col2 = st.columns(2)
            
            with col1:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"FMEA_{timestamp}"
                
                if output_format == "Excel":
                    # Create Excel file in memory
                    output_path = Path(f"output/{filename}.xlsx")
                    output_path.parent.mkdir(exist_ok=True)
                    
                    generator = initialize_generator(config)
                    generator.export_fmea(filtered_df, str(output_path), format='excel')
                    
                    with open(output_path, 'rb') as f:
                        st.download_button(
                            label="📥 Download Excel",
                            data=f,
                            file_name=f"{filename}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    csv = filtered_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"{filename}.csv",
                        mime="text/csv"
                    )
    
    with tab2:
        st.markdown('<div class="sub-header">PFMEA LLM Generator</div>', unsafe_allow_html=True)
        st.markdown("Generate PFMEA records using a form-based approach with automatic prompt generation")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### Input Form")
            
            # Process context (required)
            process_type = st.text_input(
                "Process Step",
                value="Sealing",
                help="Specify the process step (e.g., Sealing, Welding, Assembly, Painting)"
            )
            
            # Components (allow multiple)
            components_input = st.text_area(
                "Components (one per line)",
                value="Heat Sealer\nPackaging Material",
                help="Enter components involved in this process, one per line",
                height=80
            )
            
            # General failure information
            defect = st.text_input(
                "General Defect/Failure Type",
                value="Improper Seal",
                help="Enter the general defect or fault type"
            )
            
            cause = st.text_area(
                "Potential Causes (one per line)",
                value="Temperature fluctuation\nMaterial variation",
                help="Describe potential causes, one per line",
                height=80
            )
            
            effect = st.text_area(
                "Potential Effects (one per line)",
                value="Product leakage\nReduced shelf life",
                help="Describe potential effects, one per line",
                height=80
            )
            
            generate_btn = st.button("🚀 Generate Multiple Failure Modes", type="primary", use_container_width=True)
            
            st.info("💡 Tip: Enter multiple components, causes, and effects (one per line) to generate comprehensive PFMEA table")
        
        with col2:
            st.markdown("#### Generated Prompt & Results")
            
            if generate_btn:
                # Parse inputs
                components = [c.strip() for c in components_input.split('\n') if c.strip()]
                causes = [c.strip() for c in cause.split('\n') if c.strip()]
                effects = [e.strip() for e in effect.split('\n') if e.strip()]
                
                # Build the prompt dynamically
                prompt_parts = ["Generate PFMEA records"]
                
                if process_type:
                    prompt_parts.append(f"for the {process_type} process")
                
                if defect:
                    prompt_parts.append(f"with failure type '{defect}'")
                
                if components:
                    prompt_parts.append(f"analyzing components: {', '.join(components)}")
                
                prompt_text = " ".join(prompt_parts) + "."
                
                # Display generated prompt
                st.markdown("**Generated prompt:**")
                st.info(prompt_text)
                
                # Generate multiple FMEA records
                with st.spinner("Generating PFMEA records..."):
                    try:
                        generator = initialize_generator(config)
                        
                        # Create FMEA records directly without LLM extraction (use form data as-is)
                        all_fmea_records = []
                        
                        # Strategy: Generate one record per component, pairing with causes/effects
                        for i, component in enumerate(components):
                            # Pair with corresponding cause/effect or cycle through them
                            cause_text = causes[i % len(causes)] if causes else "Not specified"
                            effect_text = effects[i % len(effects)] if effects else "Not specified"
                            
                            # Create FMEA record directly (bypass extraction to preserve exact text)
                            record = {
                                'component': component,
                                'failure_mode': defect,
                                'cause': cause_text,
                                'effect': effect_text,
                                'existing_controls': 'Not specified'
                            }
                            
                            # Score the record
                            scored_record = generator.scorer.score_fmea_row(record)
                            
                            # Create DataFrame
                            record_df = pd.DataFrame([scored_record])
                            
                            # Standardize column names
                            record_df.columns = [col.replace('_', ' ').title() for col in record_df.columns]
                            record_df.rename(columns={
                                'Severity': 'Severity',
                                'Occurrence': 'Occurrence', 
                                'Detection': 'Detection',
                                'Rpn': 'Rpn',
                                'Action Priority': 'Action Priority'
                            }, inplace=True)
                            
                            all_fmea_records.append(record_df)
                        
                        # Combine all records
                        if all_fmea_records:
                            combined_df = pd.concat(all_fmea_records, ignore_index=True)
                            
                            # Add Process Step column if specified
                            if process_type:
                                combined_df.insert(0, 'Process Step', process_type)
                            
                            # Store in session state for Analytics tab
                            st.session_state['fmea_df'] = combined_df
                            st.session_state['fmea_saved'] = False
                            
                            st.success(f"✅ Generated {len(combined_df)} PFMEA record(s)")
                            
                            # Display results in a clean table format
                            display_columns = ['Process Step', 'Component', 'Failure Mode', 'Cause', 'Effect', 
                                             'Severity', 'Occurrence', 'Detection', 'Rpn', 'Action Priority']
                            # Only include Process Step if it exists
                            display_columns = [col for col in display_columns if col in combined_df.columns]
                            
                            st.dataframe(
                                combined_df[display_columns],
                                use_container_width=True,
                                hide_index=True
                            )
                            
                            # Download button
                            output_file = 'output/pfmea_form_generated.xlsx'
                            Path('output').mkdir(exist_ok=True)
                            generator.export_fmea(combined_df, output_file, format='excel')
                            
                            with open(output_file, 'rb') as f:
                                st.download_button(
                                    "📥 Download PFMEA Report",
                                    f,
                                    file_name="pfmea_generated.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                        else:
                            st.warning("No PFMEA records generated. Please check your inputs.")
                            
                    except Exception as e:
                        st.error(f"Error generating PFMEA: {e}")
                        import traceback
                        st.code(traceback.format_exc())
            else:
                st.markdown("*Fill the form and click Generate to see results*")
    
    with tab3:
        st.markdown('<div class="sub-header">🚚 Supply Chain Risk Mitigation</div>', unsafe_allow_html=True)
        st.markdown("### Real-Time Transport Optimization with Disruption Analysis")
        
        # Import mitigation module
        try:
            sys.path.append(str(Path(__file__).parent))
            from mitigation_module import (
                format_for_streamlit,
                get_route_change_summary
            )
            from mitigation_module.mitigation_solver import solve_guardian_plan, generate_impact_report
            from mitigation_module.network_config import validate_network, ROUTE_MAP
            
            # Network validation
            network_info = validate_network()
            
            col1, col2 = st.columns([2, 1])
            
            with col2:
                st.markdown("#### 🌐 Dynamic Network Status")
                st.caption("🚀 NO HARDCODING - ALL ROUTES AUTO-GENERATED")
                
                # Key metrics
                st.metric("Warehouses", network_info['num_warehouses'], help="Multiple origin points")
                st.metric("Distribution Hubs", network_info['num_hubs'], help="For multi-hop routing")
                st.metric("Total Route Options", network_info['num_total_routes'], help="Direct + Multi-hop routes")
                
                # Route breakdown
                with st.expander("📊 Route Breakdown"):
                    st.metric("Direct Routes", network_info['num_direct_routes'], help="Warehouse → City")
                    st.metric("Multi-Hop Routes", network_info['num_multihop_routes'], help="Warehouse → Hub → City")
                    st.metric("Legacy Routes (CSV)", network_info['num_routes'], help="Hardcoded for data compatibility")
                
                st.metric("Target Cities", network_info['num_clients'])
                st.metric("Supply Surplus", f"{network_info['surplus']} units")
                
                if network_info.get('dynamic_routing'):
                    st.success("✓ Dynamic Routing ENABLED")
            
            with col1:
                st.markdown("#### 🛡️ Guardian Mode - Shipment Plan")
                st.info("📦 **Intelligent Input Parsing**: System extracts quantities, budgets, dates, and priorities from your natural language input, then scans news for risks and optimizes routes.")
                
                shipment_plan = st.text_area(
                    "Enter your shipment plan:",
                    height=120,
                    placeholder="Examples:\n• I need to ship 500 units to Boston on Feb 10th\n• URGENT: Send 1000 units to Chicago with budget $20,000\n• Deliver 750 units to Seattle by 2/15\n• Ship to Miami (uses default quantity)"
                )
                
                if shipment_plan and st.button("🛡️ Activate Guardian Analysis", type="primary", use_container_width=True):
                    with st.spinner("🔍 Scanning news for risks and optimizing routes..."):
                        from mitigation_module import solve_guardian_plan
                        from mitigation_module.mitigation_solver import select_routes_with_llm
                        
                        initial_plan, mitigation_plan, risk_info, destination, requirements = solve_guardian_plan(shipment_plan)
                        
                        if initial_plan and mitigation_plan:
                            # Run LLM route analysis
                            qty = requirements.get('quantity', 1000)
                            budget = requirements.get('budget')
                            
                            llm_analysis = select_routes_with_llm(
                                destination=destination,
                                quantity=qty,
                                budget=budget,
                                risk_factor=20.0 if "ALERT" in risk_info else 1.0
                            )
                            
                            # Store results with destination filter
                            st.session_state['optimization_result'] = {
                                'initial_plan': initial_plan,
                                'mitigation_plan': mitigation_plan,
                                'impact_table': generate_impact_report(initial_plan, mitigation_plan, destination),
                                'risk_info': risk_info,
                                'destination': destination,
                                'requirements': requirements,
                                'llm_analysis': llm_analysis
                            }
                            st.success("✅ Guardian Analysis Complete!")
                            
                            # Show risk alert if found
                            if "ALERT" in risk_info:
                                st.error(f"⚠️ {risk_info}")
                            else:
                                st.success(f"✅ {risk_info}")
                        else:
                            st.error(f"❌ Analysis failed: {risk_info}")
            
            # Display optimization results
            if 'optimization_result' in st.session_state:
                result = st.session_state['optimization_result']
                initial_plan = result['initial_plan']
                mitigation_plan = result['mitigation_plan']
                destination = result.get('destination', 'Unknown')
                requirements = result.get('requirements', {})
                
                st.markdown("---")
                
                # Display Parsed Requirements
                st.markdown("### 📋 Parsed Shipment Requirements")
                req_cols = st.columns([1, 1, 1, 1])
                
                with req_cols[0]:
                    st.metric(
                        "🎯 Destination", 
                        destination if destination else "Not specified"
                    )
                
                with req_cols[1]:
                    qty = requirements.get('quantity')
                    if qty:
                        st.metric("📦 Quantity", f"{qty:,} units", help="From your input")
                    else:
                        from mitigation_module.dynamic_network import get_city_demand
                        default_qty = get_city_demand(destination)
                        st.metric("📦 Quantity", f"{default_qty:,} units", help="Default value (not specified in input)")
                
                with req_cols[2]:
                    budget = requirements.get('budget')
                    currency = requirements.get('currency', 'USD')
                    if budget:
                        st.metric("💵 Budget", format_currency(budget, currency), help="From your input")
                    else:
                        st.metric("💵 Budget", "Not specified", help="No budget constraint")
                
                with req_cols[3]:
                    date = requirements.get('date')
                    if date:
                        st.metric("📅 Delivery", date, help="From your input")
                    else:
                        st.metric("📅 Delivery", "Not specified", help="No delivery date specified")
                
                # Show priority if specified
                priority = requirements.get('priority')
                if priority:
                    st.info(f"⚡ **Priority Level:** {priority}")
                
                st.markdown("---")
                
                # Show all available routes for this destination
                st.markdown(f"### 🛣️ Available Routes for {destination}")
                
                from mitigation_module.dynamic_network import get_full_route_map
                full_route_map = get_full_route_map()
                
                # Filter routes for this destination
                available_routes = {}
                for route_id, route_tuple in full_route_map.items():
                    dest = route_tuple[-1]  # Last element is destination
                    if dest == destination:
                        available_routes[route_id] = route_tuple
                
                if available_routes:
                    # Categorize routes
                    direct_routes = {rid: r for rid, r in available_routes.items() if len(r) == 2}
                    multihop_routes = {rid: r for rid, r in available_routes.items() if len(r) == 3}
                    
                    col_route1, col_route2, col_route3 = st.columns(3)
                    
                    with col_route1:
                        st.metric(
                            "Total Route Options",
                            len(available_routes),
                            help=f"All available routes to {destination}"
                        )
                    
                    with col_route2:
                        st.metric(
                            "Direct Routes",
                            len(direct_routes),
                            help="Warehouse → City (1 hop)"
                        )
                    
                    with col_route3:
                        st.metric(
                            "Multi-Hop Routes",
                            len(multihop_routes),
                            help="Warehouse → Hub → City (2 hops)"
                        )
                    
                    # Show route details
                    with st.expander(f"📋 View All {len(available_routes)} Available Routes"):
                        st.markdown("**Direct Routes:**")
                        for rid, route in sorted(direct_routes.items()):
                            src, dst = route
                            st.text(f"  Route {rid}: {src} → {dst}")
                        
                        if multihop_routes:
                            st.markdown("\n**Multi-Hop Routes (via Hubs):**")
                            for rid, route in sorted(multihop_routes.items()):
                                src, hub, dst = route
                                st.text(f"  Route {rid}: {src} → {hub} → {dst}")
                else:
                    st.warning(f"No routes found for {destination}")
                
                st.markdown("---")
                st.markdown(f"### 📊 Route Impact Analysis - {destination}")
                st.caption("🤖 Showing ALL available routes with AI-powered selection analysis")
                
                # Display impact table using NEW format
                impact_table = result['impact_table']
                
                if not impact_table.empty:
                    # Add LLM route selection analysis
                    st.info("🧠 **AI Route Analysis**: System analyzed all available routes considering cost, reliability, and risk factors to recommend optimal routing strategy.")
                    
                    st.dataframe(
                        impact_table,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Route ID": st.column_config.TextColumn("Route ID", width="small"),
                            "Type": st.column_config.TextColumn("Type", width="small"),
                            "Route Path": st.column_config.TextColumn("Route Path", width="large"),
                            "Cost/Unit": st.column_config.TextColumn("Cost/Unit", width="small"),
                            "Availability": st.column_config.TextColumn("Availability", width="small"),
                            "Initial Qty": st.column_config.NumberColumn("Initial Qty", width="small"),
                            "Final Qty": st.column_config.NumberColumn("Final Qty", width="small"),
                            "Status": st.column_config.TextColumn("Status", width="small")
                        }
                    )
                    
                    # Display LLM Route Selection Analysis
                    if 'llm_analysis' in result:
                        llm_data = result['llm_analysis']
                        st.markdown("---")
                        st.markdown("### 🤖 AI Route Selection Reasoning")
                        
                        # Display overall analysis
                        st.success(f"**Strategy**: {llm_data['analysis']}")
                        
                        # Display selected routes with reasoning
                        col_llm1, col_llm2 = st.columns(2)
                        
                        with col_llm1:
                            st.markdown("#### 🎯 Selected Routes")
                            for route_info in llm_data['selected_routes']:
                                role_emoji = "🥇" if route_info['role'] == 'primary' else "🥈"
                                st.info(f"{role_emoji} **Route {route_info['route_id']}** ({route_info['role'].title()})\n\n{route_info['reason']}\n\n Quantity: {route_info['quantity']:,} units")
                        
                        with col_llm2:
                            st.markdown("#### 💵 Cost Analysis")
                            currency = requirements.get('currency', 'USD')
                            st.metric("Total Estimated Cost", format_currency(llm_data['total_cost'], currency))
                            st.metric("Selected Routes", len(llm_data['selected_routes']))
                            
                            # Budget compliance
                            if requirements.get('budget'):
                                budget = requirements['budget']
                                remaining = budget - llm_data['total_cost']
                                if remaining >= 0:
                                    st.success(f"✅ Within Budget: {format_currency(remaining, currency)} remaining")
                                else:
                                    st.error(f"⚠️ Over Budget: {format_currency(abs(remaining), currency)} excess")
                    
                    st.markdown("---")
                    st.markdown("### 💰 Cost Effective Analysis & Replanned Routes")
                    
                    # Calculate detailed costs
                    from mitigation_module.dynamic_network import get_route_cost, get_full_route_map
                    
                    # Load CSV for accurate costs
                    csv_path = 'Dataset_AI_Supply_Optimization.csv'
                    df_costs = None
                    if os.path.exists(csv_path):
                        df_costs = pd.read_csv(csv_path, encoding='latin1')
                        df_costs.columns = [c.strip() for c in df_costs.columns]
                    
                    full_route_map = get_full_route_map()
                    
                    # Get requested quantity (from user input or default)
                    requested_qty = requirements.get('quantity')
                    is_user_specified = requested_qty is not None
                    if not requested_qty:
                        from mitigation_module.dynamic_network import get_city_demand
                        requested_qty = get_city_demand(destination)
                    
                    # Calculate total quantities in plans
                    total_initial_qty = sum(qty for qty in initial_plan.values() if qty > 0)
                    total_mitigation_qty = sum(qty for qty in mitigation_plan.values() if qty > 0)
                    
                    # Calculate total costs
                    total_initial_cost = 0
                    total_mitigation_cost = 0
                    
                    for route_id, quantity in initial_plan.items():
                        if quantity > 0:
                            cost_per_unit = get_route_cost(route_id, df_costs)
                            total_initial_cost += cost_per_unit * quantity
                    
                    for route_id, quantity in mitigation_plan.items():
                        if quantity > 0:
                            cost_per_unit = get_route_cost(route_id, df_costs)
                            total_mitigation_cost += cost_per_unit * quantity
                    
                    # Display quantity validation
                    st.markdown("#### 📦 Shipment Volume Summary")
                    qty_col1, qty_col2, qty_col3, qty_col4 = st.columns(4)
                    
                    with qty_col1:
                        label = "Requested Quantity" if is_user_specified else "Default Quantity"
                        st.metric(
                            label,
                            f"{requested_qty:,} units",
                            help="From your input" if is_user_specified else "System default"
                        )
                    
                    with qty_col2:
                        qty_match = (total_initial_qty == requested_qty)
                        st.metric(
                            "Initial Plan Total",
                            f"{total_initial_qty:,} units",
                            delta="✓ Match" if qty_match else f"⚠ {total_initial_qty - requested_qty:+,}",
                            delta_color="normal" if qty_match else "off"
                        )
                    
                    with qty_col3:
                        qty_match_mit = (total_mitigation_qty == requested_qty)
                        st.metric(
                            "Mitigation Plan Total",
                            f"{total_mitigation_qty:,} units",
                            delta="✓ Match" if qty_match_mit else f"⚠ {total_mitigation_qty - requested_qty:+,}",
                            delta_color="normal" if qty_match_mit else "off"
                        )
                    
                    with qty_col4:
                        qty_unchanged = (total_initial_qty == total_mitigation_qty)
                        st.metric(
                            "Volume Change",
                            "None" if qty_unchanged else f"{total_mitigation_qty - total_initial_qty:+,}",
                            help="Difference in total units shipped"
                        )
                    
                    # Warning if quantities don't match
                    if not qty_match or not qty_match_mit:
                        st.warning("⚠️ Note: Plan quantities differ from requested quantity. This may indicate routing constraints or optimization adjustments.")
                    
                    st.markdown("#### 💵 Cost Comparison")
                    
                    # Get currency for display
                    currency = requirements.get('currency', 'USD')
                    
                    cost_col1, cost_col2, cost_col3, cost_col4 = st.columns(4)
                    
                    with cost_col1:
                        st.metric(
                            "Original Plan Cost",
                            format_currency(total_initial_cost, currency),
                            help=f"Total cost for {total_initial_qty:,} units using initial routes"
                        )
                    
                    with cost_col2:
                        st.metric(
                            "Mitigation Plan Cost",
                            format_currency(total_mitigation_cost, currency),
                            delta=format_currency(total_mitigation_cost - total_initial_cost, currency),
                            delta_color="inverse",
                            help=f"Total cost for {total_mitigation_qty:,} units after rerouting"
                        )
                    
                    with cost_col3:
                        cost_change_pct = ((total_mitigation_cost - total_initial_cost) / total_initial_cost * 100) if total_initial_cost > 0 else 0
                        st.metric(
                            "Cost Change %",
                            f"{cost_change_pct:+.1f}%",
                            help="Percentage change in total cost"
                        )
                    
                    with cost_col4:
                        cost_per_unit_initial = total_initial_cost / total_initial_qty if total_initial_qty > 0 else 0
                        cost_per_unit_mit = total_mitigation_cost / total_mitigation_qty if total_mitigation_qty > 0 else 0
                        st.metric(
                            "Cost per Unit",
                            format_currency(cost_per_unit_mit, currency),
                            delta=format_currency(cost_per_unit_mit - cost_per_unit_initial, currency),
                            delta_color="inverse",
                            help="Average cost per unit shipped"
                        )
                    
                    # Budget check if specified
                    if requirements.get('budget'):
                        budget = requirements['budget']
                        budget_status = "✅ Within Budget" if total_mitigation_cost <= budget else "⚠️ Over Budget"
                        budget_diff = budget - total_mitigation_cost
                        if budget_diff >= 0:
                            st.success(f"{budget_status} - {format_currency(budget_diff, currency)} remaining from {format_currency(budget, currency)} budget")
                        else:
                            st.error(f"{budget_status} - {format_currency(abs(budget_diff), currency)} over {format_currency(budget, currency)} budget")
                    
                    # Detailed Route Plan
                    st.markdown("#### 📊 Detailed Replanned Route Information")
                    
                    route_details = []
                    for route_id in sorted(set(list(initial_plan.keys()) + list(mitigation_plan.keys()))):
                        if route_id not in full_route_map:
                            continue
                            
                        initial_qty = initial_plan.get(route_id, 0)
                        mitigation_qty = mitigation_plan.get(route_id, 0)
                        
                        # Only show routes that are used in either plan
                        if initial_qty == 0 and mitigation_qty == 0:
                            continue
                        
                        # Handle both 2-tuple (direct) and 3-tuple (multi-hop)
                        route_tuple = full_route_map[route_id]
                        route_type = "Direct" if len(route_tuple) == 2 else "Multi-Hop"
                        
                        if len(route_tuple) == 2:
                            source, dest = route_tuple
                            route_path = f"{source} → {dest}"
                        else:
                            source, hub, dest = route_tuple
                            route_path = f"{source} → {hub} → {dest}"
                        
                        cost_per_unit = get_route_cost(route_id, df_costs)
                        
                        # Try to get distance and cost/km from CSV
                        distance_km = 500  # default
                        cost_per_km = 2.0  # default
                        if df_costs is not None and route_id in df_costs['Route (ID)'].values:
                            route_data = df_costs[df_costs['Route (ID)'] == route_id].iloc[0]
                            distance_km = route_data['Route Distance (km)']
                            cost_per_km = route_data['Cost per Kilometer ($)']
                        
                        initial_cost = cost_per_unit * initial_qty
                        mitigation_cost = cost_per_unit * mitigation_qty
                        
                        status = "⚪ Unchanged"
                        if initial_qty > 0 and mitigation_qty == 0:
                            status = "🔴 Stopped"
                        elif initial_qty == 0 and mitigation_qty > 0:
                            status = "🟢 Activated"
                        elif initial_qty != mitigation_qty:
                            status = "🔄 Adjusted"
                        
                        # Get currency
                        currency = requirements.get('currency', 'USD')
                        
                        route_details.append({
                            "Route ID": f"Route {route_id}",
                            "Type": route_type,
                            "Route Path": route_path,
                            "Distance (km)": f"{distance_km:.1f}",
                            "Cost/km": format_currency(cost_per_km, currency),
                            "Cost/Unit": format_currency(cost_per_unit, currency),
                            "Initial Qty": int(initial_qty),
                            "Mitigation Qty": int(mitigation_qty),
                            "Initial Cost": format_currency(initial_cost, currency),
                            "Mitigation Cost": format_currency(mitigation_cost, currency),
                            "Status": status
                        })
                    
                    if route_details:
                        route_df = pd.DataFrame(route_details)
                        st.dataframe(
                            route_df,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Download option
                        csv = route_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Detailed Route Plan (CSV)",
                            data=csv,
                            file_name=f"route_plan_{destination}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    
                    # Summary metrics
                    st.markdown("---")
                    st.markdown("### 📈 Route Change Summary")
                    
                    # Get route change summary
                    change_summary = get_route_change_summary(
                        initial_plan,
                        mitigation_plan,
                        ROUTE_MAP
                    )
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            "Total Routes",
                            f"{len([r for r in ROUTE_MAP.keys()])}"
                        )
                    
                    with col2:
                        st.metric(
                            "Active Routes (Initial)",
                            f"{len([r for r, q in initial_plan.items() if q > 0])}"
                        )
                    
                    with col3:
                        st.metric(
                            "Active Routes (Mitigation)",
                            f"{len([r for r, q in mitigation_plan.items() if q > 0])}"
                        )
                    
                    # Detailed breakdown
                    with st.expander("📋 Detailed Route Status Breakdown"):
                        col_a, col_b, col_c, col_d = st.columns(4)
                        
                        with col_a:
                            st.metric("🔴 Stopped", change_summary['stopped'])
                        with col_b:
                            st.metric("🟢 Activated", change_summary['activated'])
                        with col_c:
                            st.metric("🟡 Balanced", change_summary['balanced'])
                        with col_d:
                            st.metric("⚪ Unchanged", change_summary['unchanged'])
                
                else:
                    st.info("No significant route changes detected")
        
        except ImportError as e:
            st.error(f"Mitigation module not available: {e}")
            st.info("Make sure mitigation_module is properly installed")
    
    
    with tab4:
        st.markdown('<div class="sub-header">🔄 Multi-Model Comparison Mode</div>', unsafe_allow_html=True)
        st.markdown("Compare FMEA outputs from multiple LLMs side-by-side")
        
        # Import comparison module
        from multi_model_comparison import MultiModelComparator, ComparisonVisualizationHelper
        
        st.markdown("### 🎯 Model Selection & Input")
        
        # Model selection
        available_models = [
            "mistralai/Mistral-7B-Instruct-v0.2",
            "meta-llama/Llama-2-7b-chat-hf",
            "gpt2",
            "google/flan-t5-large",
            "Rule-based (No LLM)"
        ]
        
        selected_models = st.multiselect(
            "Select 2 or more models for comparison:",
            options=available_models,
            default=["Rule-based (No LLM)", "gpt2"],
            help="Choose at least 2 models to enable comparison. Hold Ctrl/Cmd to select multiple."
        )
        
        # Input method
        comparison_input_type = st.radio(
            "Input Type:",
            ["Text Input", "Structured File (CSV/Excel)"]
        )
        
        comparison_input_data = None
        
        if comparison_input_type == "Text Input":
            comparison_text = st.text_area(
                "Enter text for comparison:",
                height=150,
                placeholder="Paste customer reviews, failure reports, or complaint text...",
                help="This text will be analyzed by all selected models"
            )
            comparison_input_data = comparison_text
        else:
            comparison_file = st.file_uploader(
                "Upload CSV or Excel file",
                type=['csv', 'xlsx', 'xls'],
                key='comparison_file'
            )
            if comparison_file:
                comparison_input_data = comparison_file
        
        # Generate comparison
        if selected_models and len(selected_models) >= 2 and comparison_input_data and st.button("🚀 Generate Multi-Model Comparison", type="primary", use_container_width=True):
            if len(selected_models) < 2:
                st.error("Please select at least 2 models for comparison")
            else:
                with st.spinner("Generating FMEA from multiple models..."):
                    try:
                        generator = initialize_generator(config)
                        
                        # Prepare input
                        if comparison_input_type == "Text Input":
                            # Split text into meaningful chunks (by paragraphs or sentences)
                            # This allows models to extract multiple failure modes
                            text_chunks = []
                            # Split by double newline (paragraphs)
                            paragraphs = [p.strip() for p in comparison_text.split('\n\n') if p.strip()]
                            
                            if len(paragraphs) > 1:
                                # Multiple paragraphs - use them as chunks
                                text_chunks = paragraphs
                            else:
                                # Single paragraph - split by single newline or periods
                                sentences = [s.strip() for s in comparison_text.replace('\n', '. ').split('. ') if s.strip() and len(s.strip()) > 20]
                                
                                # Group sentences into chunks of 2-3 sentences each
                                chunk_size = 3
                                for i in range(0, len(sentences), chunk_size):
                                    chunk = '. '.join(sentences[i:i+chunk_size])
                                    if chunk:
                                        text_chunks.append(chunk)
                            
                            # If we ended up with no chunks, use the whole text
                            if not text_chunks:
                                text_chunks = [comparison_text]
                            
                            comparison_results = generator.generate_multi_model_comparison(
                                text_input=text_chunks,
                                model_names=selected_models,
                                is_file=False
                            )
                        else:
                            # Save file temporarily
                            temp_path = Path(f"temp_comparison_{comparison_file.name}")
                            with open(temp_path, "wb") as f:
                                f.write(comparison_file.getbuffer())
                            
                            comparison_results = generator.generate_multi_model_from_structured(
                                file_path=str(temp_path),
                                model_names=selected_models
                            )
                            
                            temp_path.unlink()
                        
                        # Store results in session state
                        st.session_state['comparison_results'] = comparison_results
                        
                        # Show summary of generated results
                        num_failure_modes = len(comparison_results['comparison_results']['comparison_df'])
                        st.success(f"✅ Multi-model comparison completed! Generated {num_failure_modes} failure modes for comparison.")
                        
                        # Debug: Show individual model results
                        with st.expander("🔍 Debug: Individual Model Results"):
                            for model_name, model_df in comparison_results['individual_results'].items():
                                st.write(f"**{model_name}**: {len(model_df)} failure modes")
                                if len(model_df) > 0:
                                    st.dataframe(model_df.head())
                        
                    except ValueError as e:
                        st.error(f"Input validation error: {e}")
                    except Exception as e:
                        st.error(f"Error during comparison: {e}")
                        import traceback
                        st.code(traceback.format_exc())
        
        # Display comparison table
        if 'comparison_results' in st.session_state:
            st.markdown("---")
            st.markdown("### 📋 Side-by-Side Comparison")
            
            results = st.session_state['comparison_results']
            comparison_df = results['comparison_results']['comparison_df']
            disagreement_matrix = results['comparison_results']['disagreement_matrix']
            individual_results = results['individual_results']
            model_names = results['comparison_results']['model_names']
            
            # Compute consensus for AI Confidence column
            from src.analytics import calculate_consensus_scores as _calc_cons
            _cons_df = _calc_cons(individual_results)
            _cons_map = {}
            if not _cons_df.empty:
                _cons_map = dict(zip(_cons_df['failure_mode'], _cons_df['confidence_label']))
            
            # Debug info
            st.info(f"📊 Comparison DataFrame has {len(comparison_df)} rows")
            
            if not comparison_df.empty:
                # Create comparison display
                comparison_display = []
                
                for idx, row in comparison_df.iterrows():
                    disagreement = disagreement_matrix.get(idx, {})
                    
                    # Determine disagreement visual
                    has_disagreement = disagreement.get('has_any_disagreement', False)
                    disagreement_level = 3 if has_disagreement else 0
                    
                    # Look up AI Confidence from consensus scores
                    fm_val = row.get('failure_mode', '')
                    ai_conf = _cons_map.get(fm_val, _cons_map.get(str(fm_val).strip(), 'N/A'))
                    
                    display_row = {
                        'Disagreement': '🔴' if disagreement_level > 0 else '🟢',
                        'AI Confidence': ai_conf,
                        'Failure Mode': row['failure_mode'],
                        'Effect': row['effect']
                    }
                    
                    # Add model scores
                    for model in model_names:
                        s_col = f'{model}_severity'
                        o_col = f'{model}_occurrence'
                        d_col = f'{model}_detection'
                        r_col = f'{model}_rpn'
                        
                        if s_col in comparison_df.columns and pd.notna(row[s_col]):
                            display_row[f'{model} S|O|D|RPN'] = f"{int(row[s_col])}|{int(row[o_col])}|{int(row[d_col])}|{int(row[r_col])}"
                        else:
                            display_row[f'{model} S|O|D|RPN'] = "N/A"
                    
                    comparison_display.append(display_row)
                
                comparison_display_df = pd.DataFrame(comparison_display)
                
                if len(comparison_display_df) > 0:
                    st.dataframe(comparison_display_df, use_container_width=True, height=400)
                else:
                    st.warning("⚠️ Comparison display is empty")
                
                # Show detailed comparison for high disagreement cases
                high_disagreement = results['comparison_results']['high_disagreement_cases']
                
                if high_disagreement:
                    st.markdown("---")
                    st.markdown("### 🔴 High Disagreement Cases")
                    st.markdown("Failure modes where models significantly differ in their assessments:")
                    
                    for i, case in enumerate(high_disagreement[:5], 1):  # Show top 5
                        with st.expander(f"**Case {i}: {case['failure_mode']}** (S-range: {case['severity_range']}, RPN-range: {case['rpn_range']})"):
                            st.markdown(f"**Failure Mode:** {case['failure_mode']}")
                            st.markdown(f"**Effect:** {case['effect']}")
                            st.markdown(f"**Disagreement Categories:** {', '.join(case['disagreement_categories'])}")
                            
                            # Show individual model scores
                            scores_data = []
                            for model in model_names:
                                if f'{model}_severity' in comparison_df.columns:
                                    model_idx = comparison_df[comparison_df['failure_mode'] == case['failure_mode']].index[0]
                                    model_row = comparison_df.loc[model_idx]
                                    
                                    # Check if model has values (not NaN)
                                    if pd.notna(model_row[f'{model}_severity']):
                                        scores_data.append({
                                            'Model': model,
                                            'Severity': int(model_row[f'{model}_severity']),
                                            'Occurrence': int(model_row[f'{model}_occurrence']),
                                            'Detection': int(model_row[f'{model}_detection']),
                                            'RPN': int(model_row[f'{model}_rpn']),
                                            'Priority': model_row[f'{model}_priority']
                                        })
                                    else:
                                        scores_data.append({
                                            'Model': model,
                                            'Severity': 'N/A',
                                            'Occurrence': 'N/A',
                                            'Detection': 'N/A',
                                            'RPN': 'N/A',
                                            'Priority': 'N/A'
                                        })
                            
                            if scores_data:
                                scores_df = pd.DataFrame(scores_data)
                                st.dataframe(scores_df, use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ No comparison data available. The models may not have produced comparable failure modes from the input text.")
                st.info("💡 Tip: Try providing more detailed text about specific failure scenarios, or try different model combinations.")
                
                # Still show individual results if available
                if individual_results:
                    st.markdown("### 📦 Individual Model Results")
                    for model_name, model_df in individual_results.items():
                        with st.expander(f"**{model_name}**: {len(model_df)} failure modes"):
                            st.dataframe(model_df, use_container_width=True)
            
            # Display comparative summary (only if comparison_df is not empty)
            if not comparison_df.empty:
                st.markdown("---")
                st.markdown("### 💡 Comparative Summary Insights")
                
                summary = results['comparison_results']['summary']
                
                if summary.get('key_insights'):
                    for insight in summary['key_insights']:
                        st.info(insight)
                
                # Model characteristics
                st.markdown("#### 🎯 Model Characteristics")
                
                col_char1, col_char2 = st.columns(2)
                
                with col_char1:
                    if summary.get('high_severity_model'):
                        st.markdown(f"**Assigns Higher Severity:** {summary['high_severity_model']}")
                    if summary.get('conservative_severity_model'):
                        st.markdown(f"**More Conservative Severity:** {summary['conservative_severity_model']}")
                
                with col_char2:
                    if summary.get('optimistic_detection_model'):
                        st.markdown(f"**Optimistic Detection:** {summary['optimistic_detection_model']}")
                    if summary.get('conservative_detection_model'):
                        st.markdown(f"**Conservative Detection:** {summary['conservative_detection_model']}")
                
                # Export comparison results
                st.markdown("---")
                st.markdown("### 💾 Export Comparison Results")
                
                # Export comparison summary
                csv_comparison = comparison_display_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Comparison Table (CSV)",
                    data=csv_comparison,
                    file_name=f"model_comparison_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
                
                # Export individual results
                with st.expander("📦 Export Individual Model Results"):
                    for model_name, model_fmea in individual_results.items():
                        csv_data = model_fmea.to_csv(index=False)
                        st.download_button(
                            label=f"📥 {model_name}",
                            data=csv_data,
                            file_name=f"fmea_{model_name.replace('/', '_')}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key=f"download_{model_name}"
                        )
        else:
            st.info("👆 Select models, input data, and click 'Generate Multi-Model Comparison' to see results")
    
    with tab5:
        st.markdown('<div class="sub-header">Analytics & Visualization</div>', unsafe_allow_html=True)
        
        if 'fmea_df' in st.session_state:
            fmea_df = st.session_state['fmea_df']
            
            # RPN Distribution
            st.plotly_chart(plot_rpn_distribution(fmea_df), use_container_width=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Priority Distribution
                st.plotly_chart(plot_priority_distribution(fmea_df), use_container_width=True)
            
            with col2:
                # Risk Matrix
                st.plotly_chart(plot_risk_matrix(fmea_df), use_container_width=True)
            
            # Top Risks
            st.plotly_chart(plot_top_risks(fmea_df), use_container_width=True)
            
            # Statistics
            st.markdown("### 📊 Statistical Summary")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**Severity**")
                st.write(fmea_df['Severity'].describe())
            
            with col2:
                st.markdown("**Occurrence**")
                st.write(fmea_df['Occurrence'].describe())
            
            with col3:
                st.markdown("**Detection**")
                st.write(fmea_df['Detection'].describe())
        else:
            st.info("Generate an FMEA first to see analytics.")

    with tab6:
        st.markdown('<div class="sub-header">🔍 Multi-Model Disagreement Heatmap & Variance Analysis</div>', unsafe_allow_html=True)
        st.markdown("Visualize where different LLMs disagree on FMEA scoring and identify low-confidence areas.")
        
        import plotly.express as px
        from src.analytics import (
            calculate_fmea_variance,
            generate_disagreement_matrix,
            generate_model_score_matrix,
            identify_high_variance_items,
            calculate_consensus_scores,
            calculate_average_agreement,
            flag_for_expert_review,
            identify_field_level_disagreements,
            prepare_box_plot_data,
            normalize_model_results,
        )
        
        if 'comparison_results' in st.session_state:
            results = st.session_state['comparison_results']
            individual_results = results.get('individual_results', {})
            model_names_list = list(individual_results.keys())
            
            if len(model_names_list) >= 2:
                metrics_list = ["Severity", "Occurrence", "Detection", "RPN"]

                # Normalize scores to 1-10 / 1-1000 scales
                norm_results = normalize_model_results(individual_results)

                # ──────────────────────────────────────
                # A. Confidence Indicator (Gauge) — top of page
                # ──────────────────────────────────────
                st.subheader("🎯 Overall Model Agreement")
                bench_cfg = config.get('benchmarking', {})
                agreement_thresh = bench_cfg.get('agreement_threshold', 0.8)
                agreement_info = calculate_average_agreement(norm_results, agreement_thresh)

                g_col1, g_col2, g_col3, g_col4 = st.columns(4)
                avg_conf = agreement_info['average_confidence']
                delta_pct = agreement_info['pct_high_agreement'] - 50  # delta vs 50% baseline
                with g_col1:
                    st.metric(
                        "Avg Confidence",
                        f"{avg_conf:.1%}",
                        delta=f"{delta_pct:+.1f}% vs 50% baseline",
                        delta_color="normal"
                    )
                with g_col2:
                    st.metric("Total Items", agreement_info['total_items'])
                with g_col3:
                    st.metric("High Agreement", agreement_info['high_count'],
                              delta=f"{agreement_info['pct_high_agreement']:.0f}%")
                with g_col4:
                    st.metric("Low Agreement", agreement_info['low_count'],
                              delta=f"-{agreement_info['low_count']}" if agreement_info['low_count'] else "0",
                              delta_color="inverse")

                st.markdown("---")

                # ──────────────────────────────────────
                # B. Disagreement Heatmap (plotly imshow)
                # ──────────────────────────────────────
                st.subheader("🔍 Model Disagreement Heatmap")
                st.markdown("Cell values represent the **standard deviation** across models. Higher values (red) = more disagreement.")
                
                disagreement_df = generate_disagreement_matrix(norm_results, metrics=metrics_list)
                
                if not disagreement_df.empty:
                    fig_heatmap = px.imshow(
                        disagreement_df,
                        text_auto=True,
                        labels=dict(x="FMEA Metric", y="Failure Mode", color="Std Dev"),
                        aspect="auto",
                        color_continuous_scale="RdYlGn_r",
                        title="Model Risk Agreement Matrix (Std Dev across LLMs)"
                    )
                    fig_heatmap.update_layout(height=max(400, len(disagreement_df) * 35))
                    st.plotly_chart(fig_heatmap, use_container_width=True)
                else:
                    st.warning("Could not generate disagreement matrix from available data.")
                
                st.markdown("---")

                # ──────────────────────────────────────
                # C. RPN Variance Chart (Box & Whisker)
                # ──────────────────────────────────────
                st.subheader("📦 RPN Variance — Box & Whisker Plot")
                st.markdown("Shows the spread of risk scores across models for each failure mode.")

                box_metric = st.selectbox(
                    "Select metric for box plot:",
                    metrics_list,
                    index=3,  # default to RPN
                    key="box_plot_metric_select"
                )

                box_df = prepare_box_plot_data(norm_results, metric=box_metric)
                if not box_df.empty:
                    fig_box = px.box(
                        box_df, x="Failure Mode", y=box_metric, color="Model",
                        title=f"{box_metric} Score Distribution Across Models",
                        points="all"
                    )
                    fig_box.update_layout(height=500, xaxis_tickangle=-45)
                    st.plotly_chart(fig_box, use_container_width=True)
                else:
                    st.info("No data available for box plot.")

                st.markdown("---")
                
                # ──────────────────────────────────────
                # D. Per-Metric Score Heatmaps (Model x FM)
                # ──────────────────────────────────────
                st.subheader("📊 Per-Metric Model Score Heatmaps")
                selected_metric = st.selectbox(
                    "Select metric to visualize:",
                    metrics_list,
                    key="heatmap_metric_select"
                )
                
                score_matrix = generate_model_score_matrix(norm_results, metric=selected_metric)
                if not score_matrix.empty:
                    fig_scores = px.imshow(
                        score_matrix,
                        text_auto=True,
                        labels=dict(x="LLM Model", y="Failure Mode", color=f"{selected_metric} Score"),
                        aspect="auto",
                        color_continuous_scale="RdYlGn_r",
                        title=f"{selected_metric} Scores by Model"
                    )
                    fig_scores.update_layout(height=max(400, len(score_matrix) * 35))
                    st.plotly_chart(fig_scores, use_container_width=True)
                
                st.markdown("---")

                # ──────────────────────────────────────
                # E. Consensus / Confidence Table
                # ──────────────────────────────────────
                st.subheader("🤝 Consensus & AI Confidence Scores")
                st.markdown(
                    "Confidence = 1 − (σ / max_range). "
                    "**High** = all models agree, **Low** = significant disagreement."
                )

                consensus_df = calculate_consensus_scores(norm_results, metrics=metrics_list)
                if not consensus_df.empty:
                    display_consensus = consensus_df.copy()
                    # Colour the confidence label
                    def _label_color(val):
                        if val == "High":
                            return "background-color: #c6efce; color: #006100"
                        elif val == "Medium":
                            return "background-color: #ffeb9c; color: #9c6500"
                        else:
                            return "background-color: #ffc7ce; color: #9c0006"

                    styled_consensus = display_consensus.style.map(
                        _label_color, subset=["confidence_label"]
                    )
                    st.dataframe(styled_consensus, use_container_width=True, height=350)
                else:
                    st.info("Not enough data for consensus scoring.")

                st.markdown("---")
                
                # ──────────────────────────────────────
                # F. Variance Analysis Table with Delta Highlighting
                # ──────────────────────────────────────
                st.subheader("📊 Variance Analysis")
                st.markdown(
                    "Fields with **high variance** (red) indicate **low AI confidence** — models disagree significantly. "
                    "Rows flagged for **Manual Expert Review** are highlighted."
                )
                
                variance_df = calculate_fmea_variance(norm_results, metrics=metrics_list)
                
                if not variance_df.empty:
                    # Expert-review flags
                    var_threshold_cfg = bench_cfg.get('variance_threshold', 2.5)
                    flagged_df = flag_for_expert_review(variance_df, variance_threshold=var_threshold_cfg)

                    # Build display columns
                    display_cols = ["failure_mode"]
                    style_cols = []
                    for m in metrics_list:
                        display_cols.extend([f"{m}_mean", f"{m}_std", f"{m}_range"])
                        style_cols.extend([f"{m}_std", f"{m}_range"])
                    display_cols.append("expert_review_flag")

                    avail_cols = [c for c in display_cols if c in flagged_df.columns]
                    display_df = flagged_df[avail_cols].copy()
                    display_df.columns = [c.replace("_", " ").title() for c in avail_cols]

                    # Highlight rows flagged for review
                    def _highlight_review(row):
                        flag_col = "Expert Review Flag"
                        if flag_col in row.index and "Expert Review" in str(row[flag_col]):
                            return ["background-color: #fff3cd"] * len(row)
                        return [""] * len(row)

                    nice_style_cols = [c.replace("_", " ").title() for c in style_cols if c.replace("_", " ").title() in display_df.columns]

                    styled_var = display_df.style.apply(_highlight_review, axis=1)
                    if nice_style_cols:
                        styled_var = styled_var.background_gradient(cmap='Reds', subset=nice_style_cols)
                    st.dataframe(styled_var, use_container_width=True, height=400)
                    
                    st.markdown("---")
                    
                    # ──────────────────────────────────────
                    # G. High Variance Items
                    # ──────────────────────────────────────
                    st.subheader("🔴 High-Variance Failure Modes")
                    variance_threshold = st.slider(
                        "Std Dev Threshold for flagging high variance:",
                        min_value=0.5, max_value=5.0, value=2.0, step=0.5,
                        key="variance_threshold_slider"
                    )
                    
                    high_var_items = identify_high_variance_items(variance_df, threshold_std=variance_threshold, metric="RPN")
                    
                    if not high_var_items.empty:
                        st.warning(f"⚠️ {len(high_var_items)} failure mode(s) exceed the RPN std dev threshold of {variance_threshold}.")
                        for _, row in high_var_items.iterrows():
                            with st.expander(f"**{row['failure_mode']}** — RPN Std: {row['RPN_std']:.2f}, Range: {row['RPN_range']:.0f}"):
                                c1, c2, c3, c4 = st.columns(4)
                                with c1:
                                    st.metric("Severity Std", f"{row['Severity_std']:.2f}")
                                with c2:
                                    st.metric("Occurrence Std", f"{row['Occurrence_std']:.2f}")
                                with c3:
                                    st.metric("Detection Std", f"{row['Detection_std']:.2f}")
                                with c4:
                                    st.metric("RPN Std", f"{row['RPN_std']:.2f}")
                                st.markdown(
                                    f"**Mean Scores:** Severity={row['Severity_mean']:.1f}, "
                                    f"Occurrence={row['Occurrence_mean']:.1f}, "
                                    f"Detection={row['Detection_mean']:.1f}, "
                                    f"RPN={row['RPN_mean']:.1f}"
                                )
                    else:
                        st.success(f"✅ No failure modes exceed the RPN std dev threshold of {variance_threshold}. Models are in reasonable agreement.")
                    
                    st.markdown("---")

                    # ──────────────────────────────────────
                    # H. Field-Level Outlier Detection
                    # ──────────────────────────────────────
                    st.subheader("🔎 Field-Level Disagreements (Outlier Detection)")
                    st.markdown(
                        "Cases where one model rates **Critical** and another rates **Minor** "
                        "for the same failure mode."
                    )

                    field_disagree = identify_field_level_disagreements(norm_results, severity_threshold=3)

                    if field_disagree:
                        for item in field_disagree[:10]:
                            with st.expander(
                                f"**{item['failure_mode']}** — {item['metric']} gap: {item['gap']:.0f}"
                            ):
                                st.markdown(
                                    f"**Highest:** {item['outlier_high_model']} "
                                    f"→ {item['outlier_high_score']:.0f}"
                                )
                                st.markdown(
                                    f"**Lowest:** {item['outlier_low_model']} "
                                    f"→ {item['outlier_low_score']:.0f}"
                                )
                                st.json(item['all_scores'])
                    else:
                        st.success("No extreme field-level disagreements detected.")

                    st.markdown("---")
                    
                    # ──────────────────────────────────────
                    # I. Export Section
                    # ──────────────────────────────────────
                    st.subheader("💾 Export Benchmark Data")
                    exp_c1, exp_c2, exp_c3 = st.columns(3)

                    with exp_c1:
                        csv_variance = flagged_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Variance Analysis (CSV)",
                            data=csv_variance,
                            file_name=f"variance_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key="download_variance_csv"
                        )
                    with exp_c2:
                        csv_disagreement = disagreement_df.to_csv()
                        st.download_button(
                            label="📥 Disagreement Matrix (CSV)",
                            data=csv_disagreement,
                            file_name=f"disagreement_matrix_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key="download_disagreement_csv"
                        )
                    with exp_c3:
                        if not consensus_df.empty:
                            csv_consensus = consensus_df.to_csv(index=False)
                            st.download_button(
                                label="📥 Consensus Scores (CSV)",
                                data=csv_consensus,
                                file_name=f"consensus_scores_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                key="download_consensus_csv"
                            )
                else:
                    st.warning("Could not compute variance from available data.")
            else:
                st.info("Need at least 2 model results for disagreement analysis. Go to the **🔄 Model Comparison** tab and run a comparison first.")
        else:
            st.info("👆 No comparison data available yet. Go to the **🔄 Model Comparison** tab, select 2+ models, and generate a comparison to see the disagreement heatmap and variance analysis here.")

    with tab7:
        st.markdown('<div class="sub-header">📈 History & Trends</div>', unsafe_allow_html=True)
        
        tracker = FMEAHistoryTracker("history")
        runs = tracker.list_runs()
        
        if not runs:
            st.info("No FMEA runs saved yet. Generate a FMEA to get started!")
        else:
            # Create tabs for different views
            history_view1, history_view2 = st.tabs(["📊 Run Comparison", "📈 Trend Chart"])
            
            with history_view1:
                st.markdown("### Compare Two Runs")
                
                col1, col2 = st.columns(2)
                
                # Run selection dropdowns
                run_labels = [f"{run['label']} ({run['timestamp'][:10]})" for run in runs]
                run_ids = [run['run_id'] for run in runs]
                
                with col1:
                    selected_run1_idx = st.selectbox(
                        "Select First Run (earlier):",
                        range(len(runs)),
                        format_func=lambda i: run_labels[i],
                        key="run1_select"
                    )
                
                with col2:
                    # Only allow selecting runs that are after the first run chronologically
                    default_idx = max(0, selected_run1_idx - 1)
                    selected_run2_idx = st.selectbox(
                        "Select Second Run (later):",
                        range(len(runs)),
                        index=default_idx,
                        format_func=lambda i: run_labels[i],
                        key="run2_select"
                    )
                
                if selected_run1_idx != selected_run2_idx:
                    run_id_1 = run_ids[selected_run1_idx]
                    run_id_2 = run_ids[selected_run2_idx]
                    
                    # Get comparison
                    comparison_df = tracker.compare_runs(run_id_1, run_id_2)
                    
                    if comparison_df is not None:
                        st.markdown("---")
                        
                        # Display comparison stats
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            improved_count = len(comparison_df[comparison_df['Status'] == 'improved'])
                            st.metric("✅ Improved", improved_count)
                        
                        with col2:
                            worsened_count = len(comparison_df[comparison_df['Status'] == 'worsened'])
                            st.metric("⚠️ Worsened", worsened_count)
                        
                        with col3:
                            new_count = len(comparison_df[comparison_df['Status'] == 'new'])
                            st.metric("🆕 New", new_count)
                        
                        with col4:
                            resolved_count = len(comparison_df[comparison_df['Status'] == 'resolved'])
                            st.metric("✔️ Resolved", resolved_count)
                        
                        st.markdown("---")
                        
                        # Display comparison table with color coding
                        st.markdown("### Detailed Comparison")
                        
                        # Create styled dataframe
                        def style_status(val):
                            if val == 'improved':
                                return 'background-color: #90EE90; color: green; font-weight: bold;'
                            elif val == 'worsened':
                                return 'background-color: #FFB6C6; color: red; font-weight: bold;'
                            elif val == 'new':
                                return 'background-color: #FFE4B5; color: orange; font-weight: bold;'
                            elif val == 'resolved':
                                return 'background-color: #87CEEB; color: blue; font-weight: bold;'
                            else:
                                return ''
                        
                        # Display the comparison table
                        st.dataframe(
                            comparison_df,
                            use_container_width=True,
                            height=500,
                            hide_index=True
                        )
                    else:
                        st.error("Could not compare the selected runs.")
                else:
                    st.warning("Please select two different runs to compare.")
            
            with history_view2:
                st.markdown("### RPN Trend Chart")
                
                trend_data = tracker.get_trend_data(limit=5)
                
                if trend_data["run_labels"]:
                    st.markdown("**Top 5 Failure Modes Over Time**")
                    
                    # Prepare data for line chart
                    trend_df_data = {
                        "Run": trend_data["run_labels"]
                    }
                    
                    num_runs = len(trend_data["run_labels"])
                    for mode in trend_data["failure_modes"]:
                        if mode in trend_data["trend_data"]:
                            values = trend_data["trend_data"][mode]
                            # Pad or trim to match run_labels length
                            if len(values) < num_runs:
                                values = values + [0] * (num_runs - len(values))
                            elif len(values) > num_runs:
                                values = values[:num_runs]
                            trend_df_data[mode] = values
                    
                    trend_df = pd.DataFrame(trend_df_data)
                    
                    # Create line chart
                    fig = px.line(
                        trend_df,
                        x="Run",
                        y=trend_data["failure_modes"],
                        title="RPN Trend for Top Failure Modes",
                        labels={"value": "RPN", "variable": "Failure Mode"},
                        markers=True
                    )
                    
                    fig.update_xaxes(tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Not enough runs to display trends.")
            
            # Display all runs as a table
            st.markdown("---")
            st.markdown("### 📋 All Saved Runs")
            
            # Convert runs to DataFrame for display
            runs_df = pd.DataFrame([
                {
                    "Run ID": run['run_id'],
                    "Label": run['label'],
                    "Timestamp": run['timestamp'],
                    "Row Count": run['row_count'],
                    "Avg RPN": f"{run['average_rpn']:.1f}",
                    "Critical Count": run['critical_count']
                }
                for run in runs
            ])
            
            st.dataframe(runs_df, use_container_width=True, hide_index=True)
    with tab8:
        st.markdown('<div class="sub-header">Help & Documentation</div>', unsafe_allow_html=True)
        
        st.markdown("""
        ## 🎯 How to Use This System
        
        ### Input Types:
        
        #### 1. Unstructured Text
        - Upload CSV files with customer reviews
        - Paste complaint text directly
        - System will extract failure modes automatically using LLM
        
        #### 2. Structured Files
        - Upload CSV/Excel with columns:
          - failure_mode (required)
          - effect (required)
          - cause (required)
          - component (optional)
          - existing_controls (optional)
        
        #### 3. Hybrid Mode
        - Combine both structured and unstructured data
        - System intelligently merges and deduplicates
        
        ### Risk Scoring:
        
        - **Severity (S)**: Impact of failure (1-10)
          - 1-3: Minor
          - 4-6: Moderate
          - 7-9: Major
          - 10: Critical/Catastrophic
        
        - **Occurrence (O)**: Likelihood of occurrence (1-10)
          - 1-3: Rare
          - 4-6: Moderate
          - 7-9: Frequent
          - 10: Almost certain
        
        - **Detection (D)**: Likelihood of detection (1-10)
          - 1-3: Almost certain to detect
          - 4-6: Moderate chance
          - 7-9: Low chance
          - 10: Almost impossible
        
        - **RPN = S × O × D** (1-1000)
        
        ### Action Priority:
        - **Critical**: RPN ≥ 500 or S ≥ 9
        - **High**: RPN ≥ 250
        - **Medium**: RPN ≥ 100
        - **Low**: RPN < 100
        
        ### Tips:
        - Focus on Critical and High priority items first
        - Use filters to focus on specific risk levels
        - Export results for team reviews
        - Monitor RPN trends over time
        """)


if __name__ == "__main__":
    main()

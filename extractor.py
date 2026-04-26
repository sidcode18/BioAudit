import pdfplumber
import torch
import re
import cv2
import numpy as np
import platform
from sentence_transformers import SentenceTransformer, util
import pytesseract
from PIL import Image

if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_biomarkers(pdf_path: str, db_markers: list) -> dict:
    extracted_results = {}
    marker_embeddings = model.encode(db_markers, convert_to_tensor=True)
    raw_text = ""
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text: raw_text += text + "\n"
    except Exception as e:
        print(f"Extraction Error: {e}")
        return extracted_results

    lines = raw_text.split('\n')
    number_pattern = re.compile(r'\b\d+(?:\.\d+)?\b')
    
    for line in lines:
        if len(line.strip()) < 3: continue
            
        matches = list(number_pattern.finditer(line))
        if not matches: continue
            
        for match in matches:
            value_str = match.group()
            value = float(value_str)
            
            if value_str.isdigit() and 1900 <= int(value) <= 2099:
                line_lower = line.lower()
                if "association" in line_lower or "guideline" in line_lower or "criteria" in line_lower:
                    continue 
            
            left_context = line[:match.start()]
            clean_context = re.sub(r'[^a-zA-Z0-9\s]', ' ', left_context).strip()
            clean_context = re.sub(r'\s+', ' ', clean_context)
            
            if len(clean_context) < 2: continue
                
            text_embedding = model.encode(clean_context, convert_to_tensor=True)
            cosine_scores = util.cos_sim(text_embedding, marker_embeddings)[0]
            
            best_match_idx = torch.argmax(cosine_scores).item()
            best_score = cosine_scores[best_match_idx].item()
            
            if best_score > 0.65:
                matched_name = db_markers[best_match_idx]
                if matched_name not in extracted_results:
                    extracted_results[matched_name] = value

    return extracted_results

def identify_supplement_from_image(image_path: str, fundamental_supplements: list) -> dict:
    try:
        raw_text = ""
        try:
            import cv2
            img = cv2.imread(image_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            custom_config = r'--oem 3 --psm 11'
            raw_text = pytesseract.image_to_string(thresh, config=custom_config)
        except ImportError:
            from PIL import Image
            custom_config = r'--oem 3 --psm 11'
            raw_text = pytesseract.image_to_string(Image.open(image_path), config=custom_config)

        cleaned_text = " ".join(raw_text.split())
        
        if len(cleaned_text) < 3:
            return {"status": "error", "message": "Text unreadable. Please ensure good lighting."}

        supp_embeddings = model.encode(fundamental_supplements, convert_to_tensor=True)
        words = cleaned_text.split()
        best_match, highest_score = None, 0
        
        for i in range(len(words)):
            for j in range(1, 4):
                if i + j <= len(words):
                    chunk = " ".join(words[i:i+j])
                    chunk_embedding = model.encode(chunk, convert_to_tensor=True)
                    scores = util.cos_sim(chunk_embedding, supp_embeddings)[0]
                    max_score_idx = torch.argmax(scores).item()
                    max_score = scores[max_score_idx].item()
                    
                    if max_score > highest_score:
                        highest_score = max_score
                        best_match = fundamental_supplements[max_score_idx]

        if highest_score > 0.65:
            return {"status": "success", "is_fundamental": True, "match": best_match, "confidence": highest_score}
        else:
            fallback_guess = " ".join(words[:3]) if words else ""
            return {"status": "success", "is_fundamental": False, "raw_text": fallback_guess}

    except Exception as e:
        return {"status": "error", "message": f"Server vision error: {str(e)}"}
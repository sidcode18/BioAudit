import pdfplumber
import torch
import re
from sentence_transformers import SentenceTransformer, util

# Load the NLP model globally so it only initializes once (saves processing time)
model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_biomarkers(pdf_path: str, db_markers: list) -> dict:
    """
    Parses a PDF, extracts numeric values, and uses Cosine Similarity 
    to map messy lab terminology to strict database terminology.
    """
    extracted_results = {}
    
    # 1. Convert standard database names into mathematical vectors
    marker_embeddings = model.encode(db_markers, convert_to_tensor=True)
    
    raw_text = ""
    try:
        # 2. Extract raw text from the PDF document
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    raw_text += text + "\n"
    except Exception as e:
        print(f"Extraction Error: {e}")
        return extracted_results

    # 3. Parse lines using Regex to isolate numeric test results
    lines = raw_text.split('\n')
    number_pattern = re.compile(r'\b\d+(?:\.\d+)?\b')
    
    for line in lines:
        if len(line.strip()) < 3:
            continue
            
        matches = list(number_pattern.finditer(line))
        if not matches:
            continue
            
        # 4. Semantic Matching Loop
        for match in matches:
            value_str = match.group()
            value = float(value_str)
            
            # Isolate the surrounding text as the "Context" (e.g., "Serum 25-OH Vit D")
            context_text = line.replace(value_str, '').strip()
            if len(context_text) < 3:
                continue
                
            # Convert context to vector and apply Cosine Similarity formula
            text_embedding = model.encode(context_text, convert_to_tensor=True)
            cosine_scores = util.cos_sim(text_embedding, marker_embeddings)[0]
            
            # Identify the highest scoring database match
            best_match_idx = torch.argmax(cosine_scores).item()
            best_score = cosine_scores[best_match_idx].item()
            
            # Confidence Threshold: 0.70 allows for variations without capturing garbage data
            if best_score > 0.70:
                matched_name = db_markers[best_match_idx]
                
                # Assign the first matched value (prevents capturing trailing reference ranges)
                if matched_name not in extracted_results:
                    extracted_results[matched_name] = value

    return extracted_results
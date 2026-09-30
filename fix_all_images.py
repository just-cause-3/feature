import json
import os
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Map local files in images/
local_images = os.listdir('images')
print(f"Total local images in images/ directory: {len(local_images)}")

# Build lookup by base filename
# e.g., 'Fast_Food_Joint-1.png' -> '2017_S1_DILR_Fast_Food_Joint-1.png'
# Also year/slot specific lookups
image_lookup = {}
for limg in local_images:
    image_lookup[limg.lower()] = f"images/{limg}"
    # Also index by suffix (e.g. Fast_Food_Joint-1.png)
    parts = limg.split('_', 3)
    if len(parts) >= 4:
        image_lookup[parts[3].lower()] = f"images/{limg}"
        image_lookup[f"{parts[0]}_{parts[1]}_{parts[2]}_{parts[3]}".lower()] = f"images/{limg}"
    elif len(parts) == 3:
        image_lookup[parts[2].lower()] = f"images/{limg}"

def clean_html_fragment(html_str, yr, slot, sec):
    if not html_str or '<img' not in html_str:
        return html_str
        
    soup = BeautifulSoup(html_str, 'html.parser')
    
    # 1. Unwrap all <noscript> tags so hidden fallback images are exposed
    for ns in soup.find_all('noscript'):
        ns.unwrap()
        
    base_url = f"https://online.2iim.com/CAT-question-paper/CAT-{yr}-Question-Paper-Slot-{slot}-{sec}/"
    
    all_imgs = soup.find_all('img')
    
    # Track seen images to avoid consecutive duplicates (lozad placeholder + noscript image)
    seen_srcs = set()
    
    for img in all_imgs:
        # Determine actual src
        src = img.get('src') or img.get('data-src') or img.get('data-original')
        if not src:
            img.decompose()
            continue
            
        src_clean = src.split('?')[0].strip()
        base_name = os.path.basename(src_clean).lower()
        
        # Filter out UI icons/banners if any leaked
        if any(x in base_name for x in ['logo', 'loading', 'popup', 'offer', 'amazon', 'sponsor', 'touch']):
            img.decompose()
            continue
            
        # Deduplication check
        if base_name in seen_srcs:
            # Duplicate image tag
            img.decompose()
            continue
        seen_srcs.add(base_name)
        
        # Find matching local image
        matched_local = None
        # Try exact year_slot_sec_basename
        spec_key = f"{yr}_s{slot}_{sec}_{base_name}".lower()
        if spec_key in image_lookup:
            matched_local = image_lookup[spec_key]
        elif base_name in image_lookup:
            matched_local = image_lookup[base_name]
        else:
            # Search for ending with base_name
            for limg in local_images:
                if limg.lower().endswith(base_name):
                    matched_local = f"images/{limg}"
                    break
                    
        remote_url = urljoin(base_url, src)
        
        if matched_local:
            img['src'] = matched_local
        else:
            img['src'] = remote_url
            
        img['data-remote-src'] = remote_url
        img['class'] = ['cat-img', 'img-fluid']
        img['style'] = "max-width:100%; height:auto; display:block; margin:0.75rem auto; border-radius:8px; cursor:zoom-in;"
        img['loading'] = "lazy"
        
        # Remove broken attributes
        if 'data-src' in img.attrs:
            del img.attrs['data-src']
        if 'width' in img.attrs and '%' in img.attrs['width']:
            del img.attrs['width']
        if 'height' in img.attrs and '%' in img.attrs['height']:
            del img.attrs['height']
            
    return "".join(str(c) for c in soup.children)

# Load dataset
with open('data/cat_pyqs.json', 'r', encoding='utf-8') as f:
    questions = json.load(f)

print(f"Processing {len(questions)} questions...")

fixed_imgs_count = 0
for q in questions:
    yr = q['year']
    slot = q['slot']
    sec = q['section']
    
    if q.get('passageHtml'):
        before = q['passageHtml']
        after = clean_html_fragment(before, yr, slot, sec)
        if before != after:
            q['passageHtml'] = after
            fixed_imgs_count += 1
            
    if q.get('questionHtml'):
        before = q['questionHtml']
        after = clean_html_fragment(before, yr, slot, sec)
        if before != after:
            q['questionHtml'] = after
            fixed_imgs_count += 1
            
    if q.get('explanationHtml'):
        before = q['explanationHtml']
        after = clean_html_fragment(before, yr, slot, sec)
        if before != after:
            q['explanationHtml'] = after

print(f"Fixed image tags in {fixed_imgs_count} HTML fragments!")

# Save back to json and js
with open('data/cat_pyqs.json', 'w', encoding='utf-8') as f:
    json.dump(questions, f, ensure_ascii=False)

with open('data/cat_data.js', 'w', encoding='utf-8') as f:
    f.write("window.CAT_DATA = ")
    json.dump(questions, f, ensure_ascii=False)
    f.write(";\n")

print("Saved updated data/cat_pyqs.json and data/cat_data.js successfully!")

import glob
import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

sys.stdout.reconfigure(encoding='utf-8')

os.makedirs('data', exist_ok=True)
os.makedirs('images', exist_ok=True)

from find_images import image_urls
url_to_local = {url: f"images/{loc}" for url, loc in image_urls.items()}

def clean_element_html(elem, base_url):
    if not elem:
        return ""
    soup = BeautifulSoup(str(elem), 'lxml')
    
    # Process images
    for img in soup.find_all('img'):
        src = img.get('src')
        if not src:
            continue
        full_src = urljoin(base_url, src)
        if full_src in url_to_local:
            img['src'] = url_to_local[full_src]
            img['data-remote-src'] = full_src
        else:
            img['src'] = full_src
        img['class'] = (img.get('class', []) or []) + ['cat-img', 'img-fluid']
        img['loading'] = 'lazy'
        
    for s in soup.find_all(['script', 'style']):
        s.decompose()
        
    # Remove ads/sponsors
    for tag in soup.find_all(lambda e: e.name in ['div', 'p', 'center'] and any(x in e.get_text().lower() for x in ['share on', 'download here', 'attempt these questions as', 'cat coaching'])):
        # don't remove if it has question content
        if not tag.find('ol', class_=lambda c: c and 'choice' in c) and len(tag.get_text()) < 150:
            tag.decompose()
            
    return "".join(str(c) for c in (soup.body.children if soup.body else soup.children)).strip()

def parse_paper(file_path):
    bn = os.path.basename(file_path).replace('.html', '')
    parts = bn.split('_')
    yr = int(parts[0])
    slot = int(parts[1].replace('S', ''))
    sec = parts[2]
    sec_map = {'Quant': 'QA', 'DILR': 'DILR', 'VARC': 'VARC'}
    sec_code = sec_map.get(sec, sec)
    base_url = f"https://online.2iim.com/CAT-question-paper/CAT-{yr}-Question-Paper-Slot-{slot}-{sec}/"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()
    soup = BeautifulSoup(html, 'lxml')
    
    ques_ols = soup.find_all('ol', class_=lambda c: c and 'ques' in c)
    questions = []
    
    if len(ques_ols) == 1:
        ol = ques_ols[0]
        curr_passage_html = ""
        for child in ol.children:
            if not getattr(child, 'name', None):
                continue
            if child.name == 'p':
                text = child.get_text(separator=' ', strip=True)
                imgs = child.find_all('img')
                if len(text) > 30 or imgs:
                    curr_passage_html = clean_element_html(child, base_url)
            elif child.name == 'li':
                q = parse_li(child, curr_passage_html, yr, slot, sec_code, base_url, len(questions) + 1)
                if q:
                    questions.append(q)
    else:
        for ol in ques_ols:
            curr = ol.previous_sibling
            pre_elems = []
            while curr:
                if getattr(curr, 'name', None):
                    if curr.name == 'ol' and curr.get('class') and 'ques' in ' '.join(curr.get('class')):
                        break
                    if curr.name in ['h2', 'header']:
                        break
                    pre_elems.insert(0, curr)
                curr = curr.previous_sibling
                
            p_parts = []
            for elem in pre_elems:
                t = elem.get_text(strip=True).lower()
                if any(x in t for x in ['share on', 'download here', 'attempt these questions as']):
                    continue
                c = clean_element_html(elem, base_url)
                if c:
                    p_parts.append(c)
            passage_html = "".join(p_parts) if p_parts else ""
            
            for li in ol.find_all('li', recursive=False):
                q = parse_li(li, passage_html, yr, slot, sec_code, base_url, len(questions) + 1)
                if q:
                    questions.append(q)
                    
    return questions

def parse_li(li, passage_html, yr, slot, sec_code, base_url, q_num):
    header_el = li.find(['h4', 'h5', 'h3'])
    header_text = header_el.get_text(strip=True) if header_el else f"CAT {yr} Slot {slot} - {sec_code}"
    
    choice_ol = li.find('ol', class_=lambda c: c and 'choice' in c)
    choices = []
    if choice_ol:
        for c_idx, c_li in enumerate(choice_ol.find_all('li')):
            choices.append({
                'key': chr(65 + c_idx),
                'text': c_li.get_text(separator=' ', strip=True),
                'html': clean_element_html(c_li, base_url)
            })
            
    ans_text = ""
    tooltip = li.find(class_='tooltiptext')
    if tooltip:
        ans_text = tooltip.get_text(separator=' ', strip=True)
    if not ans_text:
        sans = li.find(class_='Sans') or li.find(lambda e: e.name in ['p', 'span'] and '006400' in e.get('style', ''))
        if sans:
            ans_text = sans.get_text(separator=' ', strip=True)
    if not ans_text:
        ca_match = re.search(r'Correct Answer:?\s*([^\n<]+)', li.get_text(), re.IGNORECASE)
        if ca_match:
            ans_text = ca_match.group(1).strip()
            
    correct_letter = None
    ans_clean = ans_text.strip()
    match_choice = re.search(r'Choice\s*([A-D])', ans_clean, re.IGNORECASE)
    if match_choice:
        correct_letter = match_choice.group(1).upper()
    elif choices and ans_clean:
        for c in choices:
            if c['text'].strip().lower() == ans_clean.lower():
                correct_letter = c['key']
                break
                
    q_type = "MCQ" if choices else "TITA"
    
    subpage_url = ""
    for a in li.find_all('a', href=True):
        if any(x in a.get_text().strip().lower() for x in ['explanation', 'solution']):
            subpage_url = urljoin(base_url, a['href'])
            break
            
    li_soup = BeautifulSoup(str(li), 'lxml')
    for elem in li_soup.find_all(['h4', 'h5', 'h3', 'hr']):
        elem.decompose()
    for elem in li_soup.find_all(class_=lambda c: c and any(x in str(c).lower() for x in ['choice', 'tooltip', 'btn-group', 'sans'])):
        elem.decompose()
    for elem in li_soup.find_all('div', class_=lambda c: c and any(x in str(c) for x in ['span_1_of_4', 'btn-group'])):
        elem.decompose()
    for elem in li_soup.find_all('button'):
        elem.decompose()
        
    question_html = clean_element_html(li_soup.body.next_element if li_soup.body else li_soup, base_url)
    question_text = li_soup.get_text(separator=' ', strip=True)
    
    return {
        'id': f"cat_{yr}_s{slot}_{sec_code.lower()}_q{q_num}",
        'year': yr,
        'slot': slot,
        'section': sec_code,
        'qNo': q_num,
        'header': header_text,
        'type': q_type,
        'passageHtml': passage_html,
        'hasPassage': bool(passage_html.strip()),
        'questionHtml': question_html,
        'questionText': question_text,
        'choices': choices,
        'answerRaw': ans_text,
        'correctLetter': correct_letter,
        'subpageUrl': subpage_url
    }

print("Parsing all downloaded papers...")
files = sorted(glob.glob('raw_html/*.html'))
all_questions = []
for f in files:
    all_questions.extend(parse_paper(f))

print(f"Total parsed questions: {len(all_questions)}")

# Load explanation cache if exists
exp_cache_file = 'data/explanations_cache.json'
exp_cache = {}
if os.path.exists(exp_cache_file):
    try:
        with open(exp_cache_file, 'r', encoding='utf-8') as f:
            exp_cache = json.load(f)
        print(f"Loaded {len(exp_cache)} cached explanations.")
    except Exception as e:
        print("Error loading cache:", e)

# Fetch explanations in parallel
def fetch_explanation(q):
    q_id = q['id']
    if q_id in exp_cache and exp_cache[q_id].get('status') == 'OK':
        return q_id, exp_cache[q_id]
        
    url = q.get('subpageUrl')
    if not url:
        return q_id, {'status': 'NO_URL', 'video': '', 'explanation': ''}
        
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}, timeout=10)
        if r.status_code != 200:
            return q_id, {'status': f'ERR_{r.status_code}', 'video': '', 'explanation': ''}
            
        soup = BeautifulSoup(r.text, 'lxml')
        yt = soup.find('iframe')
        yt_url = yt.get('src') if yt else ""
        
        h3 = soup.find(lambda e: e.name == 'h3' and 'Explanatory Answer' in e.get_text())
        exp_parts = []
        if h3:
            curr = h3.next_sibling
            while curr:
                if getattr(curr, 'name', None):
                    t = curr.get_text().strip().lower()
                    if curr.name in ['h2', 'footer'] or any(x in t for x in ['best cat online coaching', 'cat coaching in chennai', 'share on facebook', 'share on twitter']):
                        break
                    # Clean curr html
                    cleaned_part = clean_element_html(curr, url)
                    if cleaned_part:
                        exp_parts.append(cleaned_part)
                curr = curr.next_sibling
                
        exp_html = "".join(exp_parts)
        data = {
            'status': 'OK',
            'video': yt_url,
            'explanation': exp_html
        }
        return q_id, data
    except Exception as e:
        return q_id, {'status': f'ERR_{str(e)}', 'video': '', 'explanation': ''}

to_fetch = [q for q in all_questions if q['id'] not in exp_cache or exp_cache[q['id']].get('status') != 'OK']
print(f"Fetching explanations for {len(to_fetch)} questions (concurrency=25)...")

count = 0
with ThreadPoolExecutor(max_workers=25) as executor:
    futures = {executor.submit(fetch_explanation, q): q for q in to_fetch}
    for future in as_completed(futures):
        q_id, res = future.result()
        exp_cache[q_id] = res
        count += 1
        if count % 100 == 0 or count == len(to_fetch):
            print(f"Progress: {count}/{len(to_fetch)} explanations fetched...")
            # Save periodic cache
            with open(exp_cache_file, 'w', encoding='utf-8') as f:
                json.dump(exp_cache, f, ensure_ascii=False)

# Save final cache
with open(exp_cache_file, 'w', encoding='utf-8') as f:
    json.dump(exp_cache, f, ensure_ascii=False)

# Merge into questions
for q in all_questions:
    c = exp_cache.get(q['id'], {})
    q['videoUrl'] = c.get('video', '')
    q['explanationHtml'] = c.get('explanation', '')

# Save complete dataset
with open('data/cat_pyqs.json', 'w', encoding='utf-8') as f:
    json.dump(all_questions, f, ensure_ascii=False)

with open('data/cat_data.js', 'w', encoding='utf-8') as f:
    f.write("window.CAT_DATA = ")
    json.dump(all_questions, f, ensure_ascii=False)
    f.write(";\n")

print(f"\nSUCCESS! Saved {len(all_questions)} questions to data/cat_pyqs.json and data/cat_data.js")

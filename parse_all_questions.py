import glob
import os
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Image mapping from find_images
from find_images import image_urls
url_to_local = {url: os.path.join('images', loc) for url, loc in image_urls.items()}

def clean_element_html(elem, base_url):
    """Clean HTML element, fix image paths to local and remote fallbacks, clean classes"""
    if not elem:
        return ""
    
    # Clone by parsing string
    soup = BeautifulSoup(str(elem), 'lxml')
    root = soup.body.next_element if soup.body else soup
    
    # Process images
    for img in soup.find_all('img'):
        src = img.get('src')
        if not src:
            continue
        full_src = urljoin(base_url, src)
        if full_src in url_to_local:
            local_src = url_to_local[full_src].replace('\\', '/')
            img['src'] = local_src
            img['data-remote-src'] = full_src
        else:
            img['src'] = full_src
        img['class'] = (img.get('class', []) or []) + ['cat-question-image']
        img['loading'] = 'lazy'
    
    # Remove script, style, comments
    for s in soup.find_all(['script', 'style']):
        s.decompose()
        
    return "".join(str(c) for c in (soup.body.children if soup.body else soup.children)).strip()

def extract_paper(file_path):
    bn = os.path.basename(file_path).replace('.html', '')
    parts = bn.split('_') # e.g. 2022, S1, Quant
    yr = int(parts[0])
    slot = int(parts[1].replace('S', ''))
    sec = parts[2]
    
    sec_map = {
        'Quant': 'QA',
        'DILR': 'DILR',
        'VARC': 'VARC'
    }
    sec_code = sec_map.get(sec, sec)
    
    base_url = f"https://online.2iim.com/CAT-question-paper/CAT-{yr}-Question-Paper-Slot-{slot}-{sec}/"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()
        
    soup = BeautifulSoup(html, 'lxml')
    
    ques_ols = soup.find_all('ol', class_=lambda c: c and 'ques' in c)
    questions = []
    
    if len(ques_ols) == 1:
        # Pattern A (e.g. 2021-2024, or single ol with passages interspersed)
        ol = ques_ols[0]
        curr_passage_html = ""
        
        for child in ol.children:
            if not getattr(child, 'name', None):
                continue
                
            if child.name == 'p':
                # Check if it's a passage/directions
                text = child.get_text(separator=' ', strip=True)
                imgs = child.find_all('img')
                if len(text) > 30 or imgs:
                    curr_passage_html = clean_element_html(child, base_url)
            elif child.name == 'li':
                q = parse_single_li(child, curr_passage_html, yr, slot, sec_code, base_url, len(questions) + 1)
                if q:
                    questions.append(q)
    else:
        # Pattern B (e.g. 2017-2020: multiple ol.ques blocks)
        for ol in ques_ols:
            # find preceding passage
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
                
            passage_html = ""
            p_parts = []
            for elem in pre_elems:
                t = elem.get_text(strip=True).lower()
                if any(x in t for x in ['share on', 'download here', 'attempt these questions as']):
                    continue
                cleaned = clean_element_html(elem, base_url)
                if cleaned:
                    p_parts.append(cleaned)
            if p_parts:
                passage_html = "".join(p_parts)
                
            # Parse li in this ol
            for li in ol.find_all('li', recursive=False):
                q = parse_single_li(li, passage_html, yr, slot, sec_code, base_url, len(questions) + 1)
                if q:
                    questions.append(q)
                    
    return questions

def parse_single_li(li, passage_html, yr, slot, sec_code, base_url, q_num):
    # Header
    header_el = li.find(['h4', 'h5', 'h3'])
    header_text = header_el.get_text(strip=True) if header_el else f"CAT {yr} Slot {slot} - {sec_code}"
    
    # Choice OL
    choice_ol = li.find('ol', class_=lambda c: c and 'choice' in c)
    choices = []
    if choice_ol:
        for c_idx, c_li in enumerate(choice_ol.find_all('li')):
            c_text = c_li.get_text(separator=' ', strip=True)
            c_html = clean_element_html(c_li, base_url)
            choices.append({
                'key': chr(65 + c_idx), # 'A', 'B', 'C', 'D'
                'text': c_text,
                'html': c_html
            })
            
    # Correct Answer
    ans_text = ""
    # Try tooltiptext
    tooltip = li.find(class_='tooltiptext')
    if tooltip:
        ans_text = tooltip.get_text(separator=' ', strip=True)
    if not ans_text:
        # Try p.Sans or style color:#006400
        sans = li.find(class_='Sans') or li.find(lambda e: e.name in ['p', 'span'] and '006400' in e.get('style', ''))
        if sans:
            ans_text = sans.get_text(separator=' ', strip=True)
    if not ans_text:
        # Check for any element containing "Correct Answer:"
        ca_match = re.search(r'Correct Answer:?\s*([^\n<]+)', li.get_text(), re.IGNORECASE)
        if ca_match:
            ans_text = ca_match.group(1).strip()
            
    # Detect Correct Option Letter (A, B, C, D)
    correct_letter = None
    ans_clean = ans_text.strip()
    match_choice = re.search(r'Choice\s*([A-D])', ans_clean, re.IGNORECASE)
    if match_choice:
        correct_letter = match_choice.group(1).upper()
    elif choices and ans_clean:
        # Maybe the answer directly matches the text of one choice
        for c in choices:
            if c['text'].strip().lower() == ans_clean.lower():
                correct_letter = c['key']
                break
                
    q_type = "MCQ" if choices else "TITA"
    
    # Subpage explanation link
    subpage_url = ""
    for a in li.find_all('a', href=True):
        if 'explanation' in a.get_text(strip=True).lower() or 'solution' in a.get_text(strip=True).lower():
            subpage_url = urljoin(base_url, a['href'])
            break
            
    # Extract clean question statement
    # We create a clone of li, remove choices, header, button groups, tooltips, hr
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

all_files = sorted(glob.glob('raw_html/*.html'))
print(f"Total HTML files to process: {len(all_files)}")

total_questions = 0
year_summary = {}

for f in all_files:
    qs = extract_paper(f)
    bn = os.path.basename(f).replace('.html', '')
    yr = bn.split('_')[0]
    year_summary.setdefault(yr, 0)
    year_summary[yr] += len(qs)
    total_questions += len(qs)
    # verify answers
    no_ans = sum(1 for q in qs if not q['answerRaw'])
    if no_ans > 0:
        print(f"WARNING: {bn} has {no_ans} questions with NO answer!")

print(f"\nParsing Summary:")
for yr, cnt in sorted(year_summary.items()):
    print(f"  CAT {yr}: {cnt} questions")
print(f"Total Questions Parsed: {total_questions}")

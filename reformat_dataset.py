import json
import re
from bs4 import BeautifulSoup
import sys

sys.stdout.reconfigure(encoding='utf-8')

def clean_spacing(text):
    if not text:
        return ""
    text = text.replace('Â', ' ')
    # remove internal multiple spaces and newlines
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r' ?\n ?', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

def clean_html_basics(html_str):
    if not html_str:
        return ""
    
    html_str = html_str.replace('Â', ' ')
    soup = BeautifulSoup(html_str, 'html.parser')
    
    # 1. Remove comments
    from bs4 import Comment
    for c in list(soup.find_all(string=lambda t: isinstance(t, Comment))):
        c.extract()
        
    # 2. Remove empty layout grid divs from 2IIM
    for div in list(soup.find_all('div')):
        if getattr(div, 'attrs', None) is not None:
            c_list = div.attrs.get('class', [])
            c_str = ' '.join(c_list) if isinstance(c_list, list) else str(c_list)
            if any(x in c_str for x in ['group', 'section', 'col', 'span_']):
                if not div.get_text(strip=True) and not div.find('img'):
                    div.decompose()
                    
    # 3. Unwrap all <li> tags
    for li in list(soup.find_all('li')):
        li.unwrap()
        
    # 4. Remove empty hr or p
    for hr in list(soup.find_all('hr')):
        hr.decompose()
        
    # 5. Clean text inside p tags
    for p in list(soup.find_all('p')):
        inner = p.decode_contents()
        inner = re.sub(r'\s*\n\s*', ' ', inner)
        inner = re.sub(r'[ \t]{2,}', ' ', inner).strip()
        inner = re.sub(r'(?:<br\s*/?>\s*)+$', '', inner)
        inner = re.sub(r'\s*\(TITA\)\s*$', '', inner, flags=re.IGNORECASE)
        if not inner and not p.find('img'):
            p.decompose()
        else:
            new_p = BeautifulSoup(f"<p>{inner}</p>", 'html.parser').p
            p.replace_with(new_p)
            
    res = "".join(str(c) for c in soup.children).strip()
    return res

def format_va_question(q_html, p_html):
    # First clean basic html so there are no residual divs/li
    q_clean = clean_html_basics(q_html)
    full_text = f"{p_html} {q_clean}"
    
    # 1. Sentence Insertion
    if 'sentence that is missing' in q_clean.lower() or 'sentence that is missing' in full_text.lower():
        m = re.search(r'Sentence:\s*(.*?)(?:<br\s*/?>|\n|<p>)?\s*Paragraph:\s*(.*)', q_clean, re.DOTALL | re.IGNORECASE)
        if m:
            sent = clean_spacing(re.sub(r'<[^>]+>', ' ', m.group(1)))
            para_raw = m.group(2).strip()
            # Clean para_raw from residual divs
            para_soup = BeautifulSoup(para_raw, 'html.parser')
            for div in list(para_soup.find_all('div')):
                if not div.get_text(strip=True):
                    div.decompose()
            para = "".join(str(c) for c in para_soup.children)
            para = re.sub(r'___+\s*\(?([1-4])\)?\s*___+', r'<span class="blank-chip">[\1]</span>', para)
            para = re.sub(r'^\s*<p>\s*', '', para)
            para = re.sub(r'\s*</p>\s*$', '', para)
            para = clean_spacing(para)
            return True, f'''<div class="va-badge">📍 Sentence Insertion</div>
<p class="va-instruction">There is a sentence that is missing in the paragraph below. Decide in which blank (option 1, 2, 3, or 4) the sentence best fits:</p>
<div class="va-target-sentence">
  <span class="va-target-label">Sentence to insert:</span>
  <p>{sent}</p>
</div>
<div class="va-context-box">
  <p>{para}</p>
</div>'''

    # 2. Para Summary
    sum_match = re.search(r'(The passage given below is followed by four alternate summaries.*?(?:essence of the passage\.|essence of the text\.))(?:\s*<br\s*/?>\s*)*(.*)', q_clean, re.DOTALL | re.IGNORECASE)
    if sum_match:
        inst = sum_match.group(1).strip()
        body_raw = sum_match.group(2).strip()
        body_soup = BeautifulSoup(body_raw, 'html.parser')
        for div in list(body_soup.find_all('div')):
            if not div.get_text(strip=True):
                div.decompose()
        body = clean_spacing(body_soup.get_text())
        return True, f'''<div class="va-badge">📝 Para Summary</div>
<p class="va-instruction">{inst}</p>
<div class="va-context-box"><p>{body}</p></div>'''

    # 3. Para Jumbles or Odd Sentence Out
    is_jumble = any(x in full_text.lower() for x in ['properly sequenced', 'meaningful paragraph', 'jumbled', 'odd one out', 'coherent paragraph'])
    if is_jumble:
        content_for_items = q_clean if any(x in q_clean for x in ['1.', '1:', ' 1 ']) else (p_html + " " + q_clean)
        items = re.findall(r'(?:^|\s|<br\s*/?>|<p>)([1-5])[\.\:]\s*(.*?)(?=(?:\s|<br\s*/?>|<p>)[1-5][\.\:]\s*|$)', content_for_items, re.DOTALL)
        if len(items) >= 3:
            badge = "🔍 Odd One Out" if 'odd' in full_text.lower() else "🔀 Para Jumble"
            inst_text = "Five sentences related to a topic are given below. Four of them form a coherent paragraph. Identify the odd sentence:" if 'odd' in full_text.lower() else "The sentences given below, when properly sequenced, form a coherent paragraph. Enter the correct order sequence:"
            
            items_html = ""
            for num, stext in items:
                clean_s = re.sub(r'<[^>]+>', ' ', stext)
                clean_s = clean_spacing(clean_s)
                items_html += f'''<div class="jumble-item"><span class="jumble-badge">{num}</span><span class="jumble-text">{clean_s}</span></div>'''
            return True, f'''<div class="va-badge">{badge}</div>
<p class="va-instruction">{inst_text}</p>
<div class="jumble-container">{items_html}</div>'''

    return False, q_clean

def clean_passage_html(html_str):
    if not html_str:
        return ""
    
    html_str = html_str.replace('Â', ' ')
    soup = BeautifulSoup(html_str, 'html.parser')
    
    # 1. Remove comments
    from bs4 import Comment
    for c in list(soup.find_all(string=lambda t: isinstance(t, Comment))):
        c.extract()
        
    # 2. Remove redundant site header banner tags
    for h2 in list(soup.find_all('h2')):
        t = h2.get_text(strip=True).lower()
        if 'cat' in t and ('slot' in t or 'question paper' in t):
            h2.decompose()
            
    # 3. Clean up set title (h3)
    for h3 in list(soup.find_all('h3')):
        h3['class'] = ['set-case-title']
        
    # 4. Clean paragraphs
    for p in list(soup.find_all('p')):
        inner = p.decode_contents()
        inner = re.sub(r'The passage below is accompanied by a set of questions\.\s*Choose the best answer to each question\.\s*(?:<br\s*/?>)*', '', inner, flags=re.IGNORECASE)
        paragraphs = re.split(r'(?:<br\s*/?>\s*){2,}', inner)
        if len(paragraphs) > 1:
            p_blocks = []
            for par in paragraphs:
                par_clean = clean_spacing(par)
                if par_clean:
                    p_blocks.append(f"<p>{par_clean}</p>")
            new_div = BeautifulSoup(f"<div>{''.join(p_blocks)}</div>", 'html.parser').div
            p.replace_with(new_div)
            new_div.unwrap()
        else:
            cleaned_p = clean_spacing(inner)
            if not cleaned_p and not p.find('img'):
                p.decompose()
            else:
                p.clear()
                p.append(BeautifulSoup(cleaned_p, 'html.parser'))
                
    return "".join(str(c) for c in soup.children).strip()

def clean_choice_dict(c):
    raw_html = c.get('html', '') or c.get('text', '')
    clean = re.sub(r'^\s*<li[^>]*>\s*', '', raw_html)
    clean = re.sub(r'\s*</li>\s*$', '', clean)
    clean = clean.replace('Â', ' ')
    clean = clean_spacing(clean)
    c['html'] = clean
    c['text'] = clean_spacing(re.sub(r'<[^>]+>', ' ', clean))
    return c

# Load raw parsed questions
from parse_all_questions import extract_paper
import glob
import os

print("Extracting fresh clean data from all raw_html files...")
raw_files = sorted(glob.glob('raw_html/*.html'))
all_qs = []
for f in raw_files:
    all_qs.extend(extract_paper(f))

# Load explanations cache
with open('data/explanations_cache.json', 'r', encoding='utf-8') as f:
    exp_cache = json.load(f)

# Attach explanations and video links
for q in all_qs:
    c = exp_cache.get(q['id'], {})
    q['videoUrl'] = c.get('video', '')
    q['explanationHtml'] = c.get('explanation', '')

print(f"Applying enhanced formatting on all {len(all_qs)} questions...")
va_count = 0
for q in all_qs:
    sec = q['section']
    
    # Choices
    if q.get('choices'):
        for c in q['choices']:
            clean_choice_dict(c)
            
    # VA handling
    is_va = False
    if sec == 'VARC':
        is_va, formatted_q = format_va_question(q.get('questionHtml', ''), q.get('passageHtml', ''))
        if is_va:
            va_count += 1
            q['questionHtml'] = formatted_q
            q['passageHtml'] = "" # Clear carry-over RC passage
            q['hasPassage'] = False
            
    if not is_va:
        q['questionHtml'] = clean_html_basics(q.get('questionHtml', ''))
        
    if q.get('passageHtml'):
        q['passageHtml'] = clean_passage_html(q['passageHtml'])
        
    soup_text = BeautifulSoup(q['questionHtml'], 'html.parser')
    q['questionText'] = clean_spacing(soup_text.get_text(separator=' ', strip=True))

print(f"Enhanced {va_count} VA questions across all years.")

# Save back to json and js
with open('data/cat_pyqs.json', 'w', encoding='utf-8') as f:
    json.dump(all_qs, f, ensure_ascii=False)

with open('data/cat_data.js', 'w', encoding='utf-8') as f:
    f.write("window.CAT_DATA = ")
    json.dump(all_qs, f, ensure_ascii=False)
    f.write(";\n")

print("Saved updated data/cat_pyqs.json and data/cat_data.js!")

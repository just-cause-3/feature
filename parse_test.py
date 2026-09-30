from bs4 import BeautifulSoup
import sys

sys.stdout.reconfigure(encoding='utf-8')

def parse_file(fname):
    print(f"\n====================== {fname} ======================")
    with open(fname, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')
    
    # Check all ol with class ques
    ques_ols = soup.find_all('ol', class_=lambda c: c and 'ques' in c)
    print(f"ol.ques count: {len(ques_ols)}")
    
    total_q = 0
    for idx, ol in enumerate(ques_ols):
        # find direct li children or li items
        # Note: choice also has li, so find only li that are direct children or have h4/h5
        q_lis = ol.find_all('li', recursive=False)
        if not q_lis:
            # Maybe inside divs or not direct li?
            # Let's check lis with h4/h5
            q_lis = [li for li in ol.find_all('li') if li.find(['h4', 'h5', 'h3'])]
        print(f"  OL {idx+1} has {len(q_lis)} questions")
        total_q += len(q_lis)
        
        # Check first question details
        if q_lis:
            q = q_lis[0]
            header = q.find(['h4', 'h5', 'h3'])
            h_text = header.get_text(strip=True) if header else "NO_HEADER"
            
            # Check passage or preceding elements if any
            # In ol, are there elements before li?
            passages = ol.find_all('p', recursive=False)
            
            # Check choices
            choice_ol = q.find('ol', class_=lambda c: c and 'choice' in c)
            choices = []
            if choice_ol:
                choices = [c.get_text(strip=True) for c in choice_ol.find_all('li')]
            
            # Check correct answer tooltip
            tooltip = q.find(class_='tooltiptext')
            ans = tooltip.get_text(strip=True) if tooltip else "NO_ANS"
            
            # Check images
            imgs = [img.get('src') for img in q.find_all('img')]
            
            print(f"    First Q header: {h_text}")
            print(f"    Passages in OL: {len(passages)}")
            if passages:
                print(f"    Passage text snippet: {passages[0].get_text(strip=True)[:100]}...")
            print(f"    Choices count: {len(choices)}")
            print(f"    Answer: {ans}")
            print(f"    Images in Q: {imgs}")
    
    print(f"Total questions found in {fname}: {total_q}")

for fn in ['sample.html', 'dilr_2022_s1.html', 'varc_2022_s1.html', 'dilr_2017_s1.html', 'varc_2017_s1.html']:
    parse_file(fn)

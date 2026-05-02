import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = re.compile(
    r'<!-- impeccable-variants-start.*?<div data-impeccable-variant="original">\s*(<div class="journey-stages" id="journey-stages">.*?</div>\s*</div>\s*</div>\s*<!-- Variants: insert below this line -->.*?<!-- impeccable-variants-end.*?-->)',
    re.DOTALL
)

def replacer(match):
    # we need to just extract the `<div class="journey-stages"...` down to its closing tag,
    # wait, it's easier to just use string splitting
    pass

# Let's just find the exact boundaries.
start_idx = content.find('<!-- impeccable-variants-start 368d1844-42f5-4f4c-be88-1ca7b2dfba47 -->')
end_idx = content.find('<!-- impeccable-variants-end 368d1844-42f5-4f4c-be88-1ca7b2dfba47 -->')

if start_idx != -1 and end_idx != -1:
    end_tag_len = len('<!-- impeccable-variants-end 368d1844-42f5-4f4c-be88-1ca7b2dfba47 -->')
    block = content[start_idx:end_idx + end_tag_len]
    
    # Extract original
    orig_start = block.find('<div class="journey-stages" id="journey-stages">')
    
    # Find the closing tag of journey-stages. It ends right before `</div>\n          </div>\n          <!-- Variants: insert below this line -->`
    orig_end = block.find('</div>\n          </div>\n          <!-- Variants: insert below this line -->')
    
    if orig_start != -1 and orig_end != -1:
        original_html = block[orig_start:orig_end + 6] # include the </div>
        
        new_content = content.replace(block, original_html)
        with open('templates/index.html', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Restored original HTML.")
    else:
        print("Could not find original html boundaries.")
else:
    print("Could not find variants block.")

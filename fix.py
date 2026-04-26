with open('frontend/index.html', 'r') as f:
    text = f.read()

import re
text = re.sub(r'(<th class="px-4 py-3" x-text="p"><\/th>\n[ \t]*<\/template>)', r'\1\n                                <th class="px-4 py-3">Aktion</th>', text, count=1)

with open('frontend/index.html', 'w') as f:
    f.write(text)

#created data: 11/9/2024

import re

def find_all(txt, pattern):
    return re.findall(pattern, txt)

def find_all_from_list(list, pattern):
    output = []
    for item in list:
        results = re.findall(pattern, item)
        output.extend(results)
    return output

#toan bo string deu khoi voi regex
def is_full_matching(txt, patttern):
    results = find_all(txt, patttern)
    for result in results:
        if txt == result:
            return True
    return False

IP_PATTERN = "\d{1,3}[.]\d{1,3}[.]\d{1,3}[.]\d{1,3}"
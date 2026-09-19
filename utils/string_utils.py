#updated date: 6/5/2026
from html.parser import HTMLParser
import re

class MLStripper(HTMLParser):
    def __init__(self, tag_exceptions = [], attr_exceptions = []):
        super().__init__()
        self.text = []
        self.tag_exceptions = tag_exceptions
        self.attr_exceptions = attr_exceptions

    def handle_data(self, data):
        self.text.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in self.tag_exceptions:
            attrs_str = " ".join(
                f'{k}="{v}"' for k, v in attrs if k in self.attr_exceptions
            )
            if attrs_str:
                self.text.append(f"<{tag} {attrs_str}>")
            else:
                self.text.append(f"<{tag}>")
        elif tag in ("p", "div", "br", "li"):
            self.text.append("\n")

    def handle_endtag(self, tag):
        if tag in self.tag_exceptions:
            self.text.append(f"</{tag}>")
        elif tag in ("p", "div", "li"):
            self.text.append("\n")

    def get_data(self):
        text = ''.join(self.text)
        # chuẩn hóa xuống dòng
        text = re.sub(r'\n+', '\n', text)
        text = text.replace("\xa0"," ") #\xa0 = &nbsp; trong html
        return text.strip()

def remove_html_tags(html, exceptions = []):
    tag_exceptions = []
    attr_exceptions = []
    if "table" in exceptions:
        tag_exceptions += [
                "table", "thead", "tbody", "tfoot",
                "tr", "td", "th",
                "colgroup", "col", "caption"
            ]
        attr_exceptions += [
            "rowspan", "colspan"
        ]
    s = MLStripper(tag_exceptions, attr_exceptions)
    s.feed(html)
    return s.get_data()

def levenshtein_distance(s, t):
    m = len(s)
    n = len(t)
    d = [[0] * (n + 1) for i in range(m + 1)]  

    for i in range(1, m + 1):
        d[i][0] = i

    for j in range(1, n + 1):
        d[0][j] = j
    
    for j in range(1, n + 1):
        for i in range(1, m + 1):
            if s[i - 1] == t[j - 1]:
                cost = 0
            else:
                cost = 1
            d[i][j] = min(d[i - 1][j] + 1,      # deletion
                          d[i][j - 1] + 1,      # insertion
                          d[i - 1][j - 1] + cost) # substitution   

    return d[m][n]

def find_similar_string_with_levenshtein_distance(target,list):
    results = []
    min = None
    for source in list:
        distance = levenshtein_distance(source,target)
        if not min:
            results = [source]
            min = distance
        elif distance < min:
            results = [source]
            min = distance
        elif distance == min:
            results.append(source)
    return {
        "results": results,
        "distance": min
    }

def split_two_or_many_space(source):
    #tìm chuỗi không có trong source
    special_str = "#$"
    while special_str in source:
        special_str += "#$"
    
    while "  " in source:
        source = source.replace("  ",special_str)
    
    array = source.split(special_str)
    output = [x.strip() for x in array if len(x.strip())>0]
        
    return output

#viết hoa
def uppercase(str):
	return str.upper()

#viết thường
def lowercase(str):
	return str.lower()


def clean_gmail_ui_artifacts(text: str) -> str:
    """
    Loại bỏ các thành phần giao diện web của Gmail bị lẫn vào nội dung email khi người dùng Reply,
    chẳng hạn như nút mở rộng/thu gọn nội dung trích dẫn:
    <div class="ajR" ... aria-label="Ẩn nội dung được mở rộng"...><img class="ajT" src="...cleardot.gif"></div>
    cũng như các thẻ div quote của Gmail (gmail_quote, gmail_attr...) ở cả dạng raw HTML và HTML entity (&lt;div...).
    """
    if not text:
        return ""

    working_text = text
    patterns_to_remove = [
        # Thẻ div nút mở rộng/thu gọn của Gmail (raw HTML)
        r'<div[^>]*?(?:class=[\'"][^\'"]*?\bajR\b[^\'"]*?[\'"]|aria-label=[\'"][^\'"]*?(?:Ẩn nội dung|Hiển thị nội dung|Show trimmed content|Hide expanded content)[^\'"]*?[\'"]|data-tooltip=[\'"][^\'"]*?(?:Ẩn nội dung|Hiển thị nội dung|Show trimmed content|Hide expanded content)[^\'"]*?[\'"])[^>]*?>.*?</div>',
        # Thẻ div nút mở rộng/thu gọn của Gmail (dạng HTML entity &lt;div...)
        r'&lt;div[^>]*?(?:class=[\'"][^\'"]*?\bajR\b[^\'"]*?[\'"]|aria-label=[\'"][^\'"]*?(?:Ẩn nội dung|Hiển thị nội dung|Show trimmed content|Hide expanded content)[^\'"]*?[\'"]|data-tooltip=[\'"][^\'"]*?(?:Ẩn nội dung|Hiển thị nội dung|Show trimmed content|Hide expanded content)[^\'"]*?[\'"])[^>]*?&gt;.*?&lt;/div&gt;',
        # Thẻ ảnh icon cleardot hoặc ajT
        r'<img[^>]*?(?:class=[\'"][^\'"]*?\bajT\b[^\'"]*?[\'"]|src=[\'"][^\'"]*?cleardot\.gif[^\'"]*?[\'"])[^>]*?>',
        r'&lt;img[^>]*?(?:class=[\'"][^\'"]*?\bajT\b[^\'"]*?[\'"]|src=[\'"][^\'"]*?cleardot\.gif[^\'"]*?[\'"])[^>]*?&gt;',
        # Thẻ div trích dẫn gmail_quote, gmail_attr
        r'</?div[^>]*?class=[\'"][^\'"]*?gmail_[^\'"]*?[\'"][^>]*?>',
        r'&lt;/?div[^>]*?class=[\'"][^\'"]*?gmail_[^\'"]*?[\'"][^>]*?&gt;',
    ]

    for p in patterns_to_remove:
        working_text = re.sub(p, '', working_text, flags=re.DOTALL | re.IGNORECASE)

    # Loại bỏ các thẻ HTML đơn lẻ còn sót lại nếu là văn bản email người dùng (không phải trang html hoàn chỉnh)
    if "<body" not in working_text.lower() and "<html" not in working_text.lower():
        working_text = re.sub(r'</?(?:div|span|p|br|strong|b|i|em)[^>]*>', ' ', working_text, flags=re.IGNORECASE)

    # Chuẩn hóa khoảng trắng và dòng trống
    working_text = re.sub(r'[ \t]+', ' ', working_text)
    working_text = re.sub(r'\n{3,}', '\n\n', working_text).strip()
    return working_text


def extract_reply_and_history(text: str):
    """
    Tách email thành (actual_reply, email_history):
    1. actual_reply: Nội dung mới người dùng vừa viết (đã loại bỏ trích dẫn, chữ ký và các thẻ giao diện Gmail).
    2. email_history: Toàn bộ phần lịch sử các email trao đổi trước đó (phần trích dẫn phía dưới).
    """
    if not text:
        return "", ""

    cleaned = clean_gmail_ui_artifacts(text.replace("\r\n", "\n"))
    actual_reply = ""
    email_history = ""

    # 1. Các mẫu Quote Header phân tách phần phản hồi mới với email cũ
    quote_patterns = [
        # Tiếng Việt (Gmail, Webmail, Outlook VN)
        r'(?i)\bVào\s+.*?(?:đã viết|viết)\s*:',
        r'(?i)\bNgày\s+.*?(?:đã viết|viết)\s*:',
        r'(?i)\bLúc\s+.*?(?:đã viết|viết)\s*:',
        # Tiếng Anh (Gmail, Apple Mail, Outlook EN)
        r'(?i)\bOn\s+.*?(?:wrote|written)\s*:',
        r'(?i)\bAt\s+.*?(?:wrote|written)\s*:',
        # Định dạng Header chuẩn Outlook / Exchange / Thunderbird
        r'(?im)^\s*---+\s*(?:Original Message|Tin nhắn gốc|Forwarded message|Thư được chuyển tiếp)\s*---+',
        r'(?im)^\s*_{5,}',
        r'(?im)^\s*-{5,}',
        r'(?im)^\s*(?:From|Từ):\s+.*?\n\s*(?:Sent|Ngày|Date):\s+',
        # Quoted lines bắt đầu bằng > hoặc &gt;
        r'(?m)^\s*(?:>|&gt;)+.*$'
    ]

    for pattern in quote_patterns:
        match = re.search(pattern, cleaned)
        if match:
            before_quote = cleaned[:match.start()].strip()
            after_quote = cleaned[match.start():].strip()
            if before_quote:
                cleaned = before_quote
                email_history = after_quote
                break

    # 2. Xóa các dòng trích dẫn thừa hoặc chữ ký điện thoại
    lines = cleaned.split("\n")
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">") or stripped.startswith("&gt;"):
            if not email_history:
                email_history = "\n".join(lines[lines.index(line):]).strip()
            break
        if re.match(r'(?i)^\s*(?:Sent from my|Được gửi từ|Get Outlook for).*$', stripped):
            continue
        filtered_lines.append(line)

    actual_reply = "\n".join(filtered_lines).strip()
    if not actual_reply:
        actual_reply = cleaned.strip() or text.strip()

    # Làm sạch các thẻ Gmail UI còn sót
    actual_reply = clean_gmail_ui_artifacts(actual_reply)

    # Làm sạch email_history (xóa dấu > ở đầu dòng để văn bản sáng sủa, dễ phân tích)
    if email_history:
        cleaned_history_lines = []
        for h_line in email_history.split("\n"):
            clean_h = re.sub(r'^(?:\s*>|\s*&gt;)+', '', h_line).strip()
            if clean_h:
                cleaned_history_lines.append(clean_h)
        email_history = "\n".join(cleaned_history_lines).strip()
        email_history = clean_gmail_ui_artifacts(email_history)

    return actual_reply, email_history


def extract_actual_user_reply(text: str) -> str:
    """
    Tách chính xác nội dung phản hồi mới của người dùng trong email,
    loại bỏ toàn bộ phần email cũ được trích dẫn (Quoted text, Forwarded headers,
    dấu > trích dẫn, chữ ký di động, thẻ UI Gmail...) giúp nội dung Note trên ServiceDesk
    và phân tích của AI gọn gàng, đúng trọng tâm.
    """
    actual_reply, _ = extract_reply_and_history(text)
    return clean_gmail_ui_artifacts(actual_reply)
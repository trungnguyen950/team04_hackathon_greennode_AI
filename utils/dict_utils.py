#updated date: 20/1/2026

from . import regex_utils,type_utils
import ast, json, urllib.parse, copy, re

#kiểm tra dict có tất cả keys theo yêu cầu không và trả về các keys còn thiếu
#nếu trả về 0 phần tử thì thỏa mãn điều kiện có keys
def get_missing_keys(data: dict, required_keys):
    required_keys = set(required_keys)      # chuyển về set cho tiện
    missing = required_keys - data.keys()   # các key không có trong dict
    return list(missing)

#truyền json vào url request GET
#%7B"date"%3A"2025-07-08"%7D = {"item":"2025-07-08"}
def parse_url_encode(encoded_str):
    decoded_str = urllib.parse.unquote(encoded_str)
    json_obj = json.loads(decoded_str)
    return json_obj

#lấy tất cả key theo yêu cầu, nếu không có sẽ tạo None hay trong danh sách defaults
#return True/False(có lấy đủ key hay không),new_dict
def collect_keys_and_create_new_keys_if_they_dont_exist(dict,keys,defaults=[]):
    new_dict = {}
    no_new = True
    for  i in range(len(keys)):
        key = keys[i]
        if key in dict:
            new_dict[key] = dict[key]
        else:
            no_new = False
            value = None
            if defaults and len(defaults) > i:
                value = defaults[i]
            new_dict[key] = value
    return no_new,new_dict
    

#chèn thêm các keys với giá trị default để chúng có khi truy vấn
def create_new_keys_if_they_dont_exist(dict, keys, defaults = []):
    for  i in range(len(keys)):
        key = keys[i]
        if key not in dict:
            value = None
            if defaults and len(defaults) > i:
                value = defaults[i]
            dict[key] = value
    return

#tạo 1 dict mới chỉ với các keys (không bắt buộc phải có hết keys)
def make_copy_with_specific_keys(dict, target_keys):
    new_dict = {}
    for target_key in target_keys:
        if target_key in dict:
            new_dict[target_key] = dict[target_key]
    return new_dict

#Chia làm 2 dictionary 1 là có keys 2 là không có key
def split(dict, target_keys):
    dict_has_keys = {}
    dict_has_no_keys = {}
    for dict_key in dict.keys():
        if dict_key in target_keys:
            dict_has_keys[dict_key] = dict[dict_key]
        else:
            dict_has_no_keys[dict_key] = dict[dict_key]

    return dict_has_keys,dict_has_no_keys


#đổi một số key theo dict_map {"value": "new_value", ...}, value kieu string
def change_values(dict, values_map):
    print(dict)
    new_dict = {}
    for dict_key in dict.keys():
        value = dict[dict_key]
        if type_utils.get_type(value) == "str":
            if value in values_map:
                new_dict[dict_key] = values_map[value]
            else:
                new_dict[dict_key] = value
        elif type_utils.get_type(value) == "list":
            list = value
            new_list = []
            for item in list:
                if type_utils.get_type(item) == "str":
                    if item in values_map:
                        new_value = values_map[item]
                        new_list.append(new_value)
                    else:
                        new_list.append(item)
                elif type_utils.get_type(item) == "dict":
                     sub_dict = change_values(item, values_map)
                     new_list.append(sub_dict)
                else:
                    new_list.append(item)
            new_dict[dict_key] = new_list
        elif type_utils.get_type(value) == "dict":
            sub_dict = change_values(value, values_map)
            new_dict[dict_key] = sub_dict
        else:
            new_dict[dict_key] = value
    return new_dict


#đổi một số key theo keys_map {"key": "new_key", ...}
def change_keys(dict, keys_map):
    new_dict = {}
    for dict_key in dict.keys():
        if dict_key in keys_map:
            new_dict[keys_map[dict_key]] = dict[dict_key]
        else:
            new_dict[dict_key] = dict[dict_key]
    return new_dict

#tạo dict với cặp key-value có input string fotmat có dạng  key<\t>value
def create_dict_with_string_format(string_format_lines):
    dict = {}
    for line in string_format_lines:
        if len(line) > 0:
            words = line.split("	")
            if len(words) == 2:
                dict[words[0]] = words[1]
            else:
                print("DICT_UTIL_ERROR:create_dict_with_string_format: wrong string format")
    return dict

#kiểm tra có key và nếu có key thì value có giá trị đó không
def check_key_value(dict, target_key, target_value):
    if target_key in dict and dict[target_key] == target_value:
        return True
    return False

#input: target_index = 0, list = [
#           ["AAA","AAA1111"],["AAA","AAA2222"],["BBB","BBB111"] 
#        ]
#output = {
#           "AAA": [["AAA","AAA1111"],["AAA","AAA2222"]]
#           "BBB": [["BBB","BBB111"]]
#         }
def group_by_one_item_in_list_of_items(list, target_index):
    dict = {}
    for row in list:
        key = row[target_index]
        if key in dict:
            dict[key].append(row)
        else:
            list = [row]
            dict[key] = list
    return dict

#str -> dict (đảo chiều dict -> json dùng str)
def parse(s):
    """
    if str:
        return ast.literal_eval(str)
    return None
    """
    s = s.strip()
    # 2. Thử kiểu dict Python
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError):
        pass
    # 1. Thử kiểu JSON
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # 3. Thử kiểu custom: "key=value; key2=value2; key3=[val1,val2]"
    if ";" in s and "=" in s:
        result = {}
        pairs = re.split(r';\s*', s)
        for pair in pairs:
            if not pair:
                continue
            key, value = pair.split("=", 1)
            key = key.strip()
            value = value.strip()
            
            # Tự động chuyển đổi list hoặc giữ nguyên chuỗi
            if value.startswith("[") and value.endswith("]"):
                try:
                    result[key] = ast.literal_eval(value)
                except:
                    result[key] = value
            else:
                result[key] = value
        return result
    raise ValueError("⚠️ Không nhận dạng được định dạng chuỗi đầu vào.")   
    
#chuyển các class object sang str()
def __object_to_str(dict):
    new_dict = {}
    for dict_key in dict.keys():
        value = dict[dict_key]
        if type_utils.get_type(value) == "class":
            new_dict[dict_key] = str(value)
        elif type_utils.get_type(value) == "list":
            list = value
            new_list = []
            for item in list:
                if type_utils.get_type(item) == "class":
                    new_list.append(str(item))
                elif type_utils.get_type(item) == "dict":
                     sub_dict = __object_to_str(item)
                     new_list.append(sub_dict)
                else:
                    new_list.append(item)
            new_dict[dict_key] = new_list
        elif type_utils.get_type(value) == "dict":
            sub_dict = __object_to_str(value)
            new_dict[dict_key] = sub_dict
        else:
            new_dict[dict_key] = value
    return new_dict
    
def to_str(dict):
    if type_utils.get_type("command") == "dict":
        new_dict = __object_to_str(dict)
        return str(new_dict)
    return str(dict)


#merge cả 2 key của 2 dict làm 1 (nếu có trùng sẽ ưu tiên dict2)
def merge_dicts(dict1,dict2):
    return {**dict1,**dict2}

def clone(dict):
    return copy.deepcopy(dict)
    
def remove_key(dict,key):
    dict.pop(key,None)

#tìm cấu trúc của object
#d = {
#    "A": [
#        {"A1": "valueA1"},
#        {"A2": "valueA2", "A3": [{"A33": "valueA33"},{"A44":"valueA44"}]}
#    ],
#    "B": "valueB"
#}
#output: ['[A].A1','[A].A2','[A].[A3].A33','[A].[A3].A44','B']
#parent_keys '' dùng cho đệ quy
#output: ['A.A1', 'A.A2', 'A.A3.A33', 'B']
def flatten_keys(d, parent_key=''):
    keys = []
    if isinstance(d, dict):
        for k, v in d.items():
            full_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                keys.extend(flatten_keys(v, full_key))
            elif isinstance(v, list):
                list_key = f"{parent_key}.[{k}]" if parent_key else f"[{k}]"
                for item in v:
                    if isinstance(item, (dict, list)):
                        keys.extend(flatten_keys(item, list_key))
                    else:
                        keys.append(list_key)
            else:
                keys.append(full_key)
    elif isinstance(d, list):
        for item in d:
            if isinstance(item, (dict, list)):
                keys.extend(flatten_keys(item, parent_key))
            else:
                keys.append(parent_key)
    return list(set(keys))  # dùng set để loại trùng khóa nếu có

#kiểm tra dict có flatten key không - ko lấy giá trị
def has_flatten_key(d, key):

    def _exists(obj, parts):
        if not parts:
            return True

        part = parts[0]

        # --- [A] ---
        if part.startswith("[") and part.endswith("]"):
            key_name = part[1:-1]

            if isinstance(obj, dict):
                sub = obj.get(key_name)
                if isinstance(sub, list):
                    return any(_exists(item, parts[1:]) for item in sub)
                return False

            elif isinstance(obj, list):
                return any(_exists(item, parts) for item in obj)

            return False

        # --- key thường ---
        else:
            if isinstance(obj, list):
                return any(
                    isinstance(item, dict) and part in item and
                    _exists(item[part], parts[1:])
                    for item in obj
                )

            elif isinstance(obj, dict):
                if part in obj:
                    return _exists(obj[part], parts[1:])
                return False

            return False

    return _exists(d, key.split("."))

#
#path lấy từ flatten_keys
#d = {
#    "A": [
#        {"A1": "valueA1"},
#        {"A2": "valueA2", "A3": [{"A33": "valueA33"},{"A44":"valueA44"}]}
#    ],
#    "B": "valueB"
#}
#output: 
#  '[A].A1' => ['valueA1', None]
#  '[A].A2' => [None, 'valueA2']
#  '[A].[A3].A33' => [None, ['valueA33', None]]
#  '[A].[A3].A44' => [None, [None, 'valueA44']]
#  'B' => 'valueB' 
def get_value_by_flatten_key(d, key):
    
    def _get_values(obj, parts):
        if not parts:
            return obj

        part = parts[0]

        # --- Nếu là [A] ---
        if part.startswith("[") and part.endswith("]"):
            key_name = part[1:-1]

            if isinstance(obj, dict):
                sub = obj.get(key_name)
                if sub is None:
                    return None
                elif isinstance(sub, list):
                    # Duyệt từng phần tử trong list
                    return [_get_values(item, parts[1:]) for item in sub]
                else:
                    return _get_values(sub, parts[1:])

            elif isinstance(obj, list):
                # Duyệt từng phần tử của list cha
                return [_get_values(item, parts) for item in obj]

            else:
                return None

        # --- Khóa bình thường ---
        else:
            if isinstance(obj, list):
                results = []
                for item in obj:
                    if isinstance(item, dict) and part in item:
                        results.append(_get_values(item[part], parts[1:]))
                    else:
                        results.append(None)
                return results

            elif isinstance(obj, dict):
                if part in obj:
                    return _get_values(obj[part], parts[1:])
                else:
                    return None

            else:
                return None

    parts = key.split(".")
    return _get_values(d, parts)

#key_path: keyA.keyB.keyC.keyD = value (không có thì sẽ tạo)
def set_value_by_flatten_key(target, flatten_key, value, separator = "."):
    keys = flatten_key.split(separator)
    cur = target

    for key in keys[:-1]:
        if key not in cur or not isinstance(cur[key], dict):
            cur[key] = {}
        cur = cur[key]

    cur[keys[-1]] = value
    

def create_dict_from_flatten_keys(flatten_keys_dict):
    result = {}

    for key, value in flatten_keys_dict.items():
        parts = key.split(".")
        current = result

        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    return result
    
#tao custom dict nhan regex lam key
class Regex_Dict:
    
    regular_dict = None
    regex_dict = None
    
    def __init__(self):
        self.regex_dict = {}
        self.regular_dict = {}
    
    def __contains_by_regular_dict(self,key):
        return key in self.regular_dict
        
    def __contains_by_regex_dict(self,key):
        for regex_key in self.regex_dict.keys():
            if regex_utils.is_full_matching(key,regex_key):
                return True
        return False

        
    def __contains__(self, key):
        if self.__contains_by_regular_dict(key):
            return True
        return self.__contains_by_regex_dict(key)

   
    def get(self, key, default=None):
        # Regular match
        if key in self.regular_dict:
            return self.regular_dict[key]
    
        # Regex match → chọn pattern dài nhất
        matched = []
        for regex_key, value in self.regex_dict.items():
            if regex_utils.is_full_matching(key, regex_key):
                matched.append((len(regex_key), value))
    
        if matched:
            matched.sort(reverse=True)  # ưu tiên pattern dài nhất
            return matched[0][1]
    
        return default
        
    #string format: key<\t>value
    def load_dict_with_string_format(self,string_format_lines):
        
        regex_keyword = "[REGEX]"
        keyword_len = len(regex_keyword)
        
        dict = create_dict_with_string_format(string_format_lines)
        for key in dict.keys():
            if regex_keyword in key:
                self.regex_dict[key[keyword_len:]] = dict[key]
            else:
                self.regular_dict[key] = dict[key]
                
                
"""
--- logs ---
group_by_one_value_in_list_of_values(dicts, target_key) => dict_list_utils.group_by_field_value(dicts, target_key)
export_values_have_the_same_key_in_dict_list(dict_list,target_key) => dict_list_utils.export_values_have_the_same_key(dict_list,target_key)
sort_dict_list_by_key(dict_list, target_key, descent = False) => dict_list_utils.sort(dict_list, target_key, descent = False)
dist_list_remove_all_keys(dict_list,key) => dict_list_utils.remove_key(dict_list,key)

"""                
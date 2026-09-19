#updated date: 10/9/2026
import pprint, json, requests, urllib3
from . import dict_utils, date_utils, type_utils, string_utils

#TỪ ĐIỂN CODE
#0: Kết quả thành công
#201: Lỗi hệ thống
#305: Lỗi xác thực 

AUTHTOKEN = "01169906-D606-4BB3-8E01-4DE4D8AE6B65"
SVD_URL = "https://49.213.71.61:8089"

def load_config(input):
    global AUTHTOKEN
    global SVD_URL
    if "authen_token" in input:
        AUTHTOKEN = input["authen_token"]
    if "servicedesk_url" in input:
        SVD_URL = input["servicedesk_url"]        

def __parse_response_status(response):
    response_status = response["response_status"]

    if type_utils.get_type(response_status) == "list":
        response_status = response_status[0]

    if response_status["status_code"] == 2000: #success
        status = {"code":0,"messages":[]}
    else: #== 4000    
        status = {"code":201,"messages":[]}
        
        if "messages" in response_status:
            messages = response_status["messages"]
            for message in messages:
                if "message" in message:
                    status["messages"].append(message["message"])
                #code của svd đã biết -> chuyển về code chung
                if "status_code" in message and message["status_code"] == 401: 
                    status["code"] = 305
    return status

def get_service_request_by_id(id, key_mappings = {
           "attachments":"[attachments].name",
           "id": "id",
           "requester": "requester.email_id",
           "department": "requester.department.name",
            "devision": "requester.department.site.name",
            "location": "site.name",
            "level": "level.name",
            "techinician": "technician.email_id",
            "techinician_name": "technician.name",
            "technician_department": "technician.department.name",
            "status": "status.name",
            "category": "category.name",
            "subcategory": "subcategory.name",
            "description": "description",
            "resolution": "resolution.content",
            "request_type":"request_type.name",
            "root_cause_type": "udf_fields.udf_pick_2401",
            "root_cause_text": "udf_fields.udf_sline_2402",
            "due_by_time": "due_by_time.display_value",
            "created_time": "created_time.display_value",
            "subject":"subject",
            "resolved_time": "resolved_time.display_value",
            "responded_time": "responded_time.display_value",
            "first_response_due_by_time": "first_response_due_by_time.display_value",
            "service_category": "service_category.name",
            "item": "item.name",
            "group": "group.name"
},log = None):
    url = f"{SVD_URL}/api/v3/requests/"+id
    headers ={"authtoken":AUTHTOKEN}
    response = requests.get(url,headers=headers,verify=False)
    res_obj = json.loads(response.text)
    try:
        pprint.pprint(res_obj)
    except Exception:
        pass

    status = __parse_response_status(res_obj)
    if log is not None:
        log["code"] = status["code"]
        log["messages"] = status["messages"]

    if status["code"] == 0:
        target_request = res_obj["request"]
        output = {}
        for key in key_mappings:
            flatten_key = key_mappings[key]
            value = dict_utils.get_value_by_flatten_key(target_request,flatten_key)
            output[key] = value
        return output
    return None

#kiểm tra request có thuộc tính đó không
def has_service_request_attribute(id, key_path, log = None):
    url = f"{SVD_URL}/api/v3/requests/"+id
    headers ={"authtoken":AUTHTOKEN}
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.get(url,headers=headers,verify=False)
    object = json.loads(response.text)
    #pprint.pprint(object)

    status = __parse_response_status(object)
    if log is not None:
        log["code"] = status["code"]
        log["messages"] = status["messages"]
        
    if status["code"] == 0:
        target_request = object["request"]
        exists = dict_utils.has_flatten_key(target_request, key_path)
        return exists     
    return None

def filter_service_requests(top_n, search_criteria, log = None):
    ids = []

    url = f"{SVD_URL}/api/v3/requests"
    headers ={"authtoken":AUTHTOKEN}
    input_data = '''{
        "list_info": {
            "row_count": '''+str(top_n)+''',
            "start_index": 1,
            "sort_field": "id",
            "sort_order": "desc",
            "get_total_count": true,
            "search_criteria": '''+dict_utils.to_str(search_criteria)+'''
        }
    }'''
    params = {'input_data': input_data}
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.get(url,headers=headers,params=params,verify=False)
    #pprint.pprint(object)
    object = json.loads(response.text)
    #pprint.pprint(objects)

    status = __parse_response_status(object)
    if log is not None:
        log["code"] = status["code"]
        log["messages"] = status["messages"]
    
    if status["code"] == 0:
        service_requests = object["requests"]
        for request in service_requests:
            ids.append(request["id"])
        return ids
    return ids

def add_resolution(id, resolution, log = None):
    url = f"{SVD_URL}/api/v3/requests/"+id+"/resolutions"
    headers ={"authtoken":AUTHTOKEN}
    input_data = '''{
        "resolution": {
            "content": "'''+resolution+'''"
        }
    }'''
    data = {'input_data': input_data}
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.post(url,headers=headers,data=data,verify=False)
    object = json.loads(response.text)

    status = __parse_response_status(object)
    if log is not None:
        log["code"] = status["code"]
        log["messages"] = status["messages"]

    if status["code"] == 0:
        return True
    return False
        
def close_request(id, comments, log = None):
    url = f"{SVD_URL}/api/v3/requests/"+id+"/close"
    headers ={"authtoken":AUTHTOKEN}
    input_data = '''{
        "request": {
            "closure_info": {
                "requester_ack_resolution": true,
                "requester_ack_comments": "'''+comments+'''",
                "closure_comments": "'''+comments+''''",
                "closure_code": {
                    "name": "success"
                }
            }
        }
    }'''
    data = {'input_data': input_data}
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.put(url,headers=headers,data=data,verify=False)
    object = json.loads(response.text)

    status = __parse_response_status(object)
    if log is not None:
        log["code"] = status["code"]
        log["messages"] = status["messages"]

    if status["code"] == 0:
        return True
    return False

"""    
def filter_users(i,search_fields,log = None):
    url = f"{SVD_URL}/api/v3/users"
    headers ={"authtoken":"99C029A7-A5BC-4C23-8A0D-64147F103208"}
    input_data = '''{
        "list_info": {
            "start_index": '''+str(i)+''',
            "row_count": "200",
            "get_total_count": true,
            "search_fields": '''+dict_utils.to_str(search_fields)+'''
        },
        "fields_required": [
            "name",
            "is_technician",
            "citype",
            "login_name",
            "email_id",
            "department",
            "phone",
            "mobile",
            "jobtitle",
            "project_roles",
            "employee_id",
            "first_name",
            "middle_name",
            "last_name",
            "is_vipuser",
            "ciid"
        ]
    }'''
    params = {'input_data': input_data}
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)    
    response = requests.get(url,headers=headers,params=params,verify=False)
    #print(response.text)    
    key_mappings = {
        "email":"email_id",
        "jobtitle":"jobtitle",
        "mobile":"mobile",
        "employee_id":"employee_id",
        "site":"department.site.name",
        "department": "department.name"
        
    }
    object = json.loads(response.text)  
    #print(object)      
    if len(object["response_status"]) > 0 and object["response_status"][0]["status"] == "success":
        users = object["users"]
        outputs = []
        for user in users:
            output = {}
            for key in key_mappings:
                flatten_key = key_mappings[key]
                value = dict_utils.get_value_by_flatten_key(user,flatten_key)
                output[key] = value
            outputs.append(output)
        if log is not None:
            log["code"] = 0
            log["messages"] = []
        return outputs
    else: #object["response_status"]["status"] == "failed"
        messages = []
        if "messages" in object["response_status"]:
            for message in object["response_status"]["messages"]:
                messages.append(message["message"])
        if log is not None:
            log["code"] = 201
            log["messages"] = messages
        return None    
"""

def filter_users(search_criteria, log = None):
    get_more = True
    row_max_count = 100 
    start_index = 1
    outputs = []
    key_mappings = {"id":"id","email":"email_id","jobtitle":"jobtitle","department":"department.name","site":"department.site.name","name":"name"}

    while(get_more):
        get_more = False
        url = f"{SVD_URL}/api/v3/users"
        headers ={"authtoken":AUTHTOKEN}
        input_data = '''{
            "list_info": {
                "sort_field": "name",
                "start_index": '''+str(start_index)+''',
                "sort_order": "asc",
                "row_count": '''+str(row_max_count)+''',
                "get_total_count": true,
                "search_criteria": '''+dict_utils.to_str(search_criteria)+'''
            },
            "fields_required": [
                "name",
                "citype",
                "login_name",
                "email_id",
                "department",
                "phone",
                "mobile",
                "jobtitle",
                "project_roles",
                "employee_id",
                "first_name",
                "middle_name",
                "last_name",
                "is_online",
                "is_vipuser",
                "ciid"
            ]
        }'''
        params = {'input_data': input_data}
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)    
        response = requests.get(url,headers=headers,params=params,verify=False)
        #print(response.text)
        object = json.loads(response.text)
        #pprint.pprint(object)

        status = __parse_response_status(object)
        if log is not None:
            log["code"] = status["code"]
            log["messages"] = status["messages"]
    
        if status["code"] == 0:
            technicians = object["users"]
            if len(technicians) == 0:
                return outputs          
            else:
                for technician in technicians:
                    output = {}
                    for key in key_mappings:
                        flatten_key = key_mappings[key]
                        value = dict_utils.get_value_by_flatten_key(technician,flatten_key)
                        output[key] = value
                    outputs.append(output)
                get_more = True
        start_index += row_max_count

    return outputs           
    
def filter_technicians(search_criteria, log = None):
    get_more = True
    row_max_count = 100 
    start_index = 1
    outputs = []
    key_mappings = {"email":"email_id","jobtitle":"jobtitle","department":"department.name","site":"department.site.name","name":"name"}

    while(get_more):
        get_more = False
        url = f"{SVD_URL}/api/v3/technicians"
        headers ={"authtoken":AUTHTOKEN}
        input_data = '''{
            "list_info": {
                "sort_field": "name",
                "start_index": '''+str(start_index)+''',
                "sort_order": "asc",
                "row_count": '''+str(row_max_count)+''',
                "get_total_count": true,
                "search_criteria": '''+dict_utils.to_str(search_criteria)+'''
            },
            "fields_required": [
                "name",
                "citype",
                "login_name",
                "email_id",
                "department",
                "phone",
                "mobile",
                "jobtitle",
                "project_roles",
                "employee_id",
                "first_name",
                "middle_name",
                "last_name",
                "is_online",
                "is_vipuser",
                "ciid"
            ]
        }'''
        params = {'input_data': input_data}
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)    
        response = requests.get(url,headers=headers,params=params,verify=False)
        object = json.loads(response.text)
        #pprint.pprint(object)
        status = __parse_response_status(object)
        if log is not None:
            log["code"] = status["code"]
            log["messages"] = status["messages"]
    
        if status["code"] == 0:
            technicians = object["technicians"]
            if len(technicians) == 0:
                return outputs          
            else:
                for technician in technicians:
                    output = {}
                    for key in key_mappings:
                        flatten_key = key_mappings[key]
                        value = dict_utils.get_value_by_flatten_key(technician,flatten_key)
                        output[key] = value
                    outputs.append(output)
                get_more = True
        start_index += row_max_count
    return outputs           

def create_service_request(input,log=None):
    
    flatten_keys_map = {
                "department": "requester.department.name",
                "devision": "requester.department.site.name",
                "location": "site.name",
                "level": "level.name",
                "requester": "requester.email_id",
                "requester_name": "requester.name",
                "technician": "technician.email_id",
                "technician_name": "technician.name",
                "technician_department": "technician.department.name",
                "status": "status.name",
                "category": "category.name",
                "subcategory": "subcategory.name",
                "description": "description",
                "resolution": "resolution.content",
                "request_type":"request_type.name",
                "root_cause_type": "udf_fields.udf_pick_2401",
                "root_cause_text": "udf_fields.udf_sline_2402",
                "subject":"subject",
                "service_category": "service_category.name",
                "item": "item.name",
                "group": "group.name"
    }
    
    input2 = {}
    exceptions = []
    for key in input.keys():
        if key in flatten_keys_map:
            input2[flatten_keys_map[key]] = input[key]
        else:
            exceptions.append(key)
    input3 = dict_utils.create_dict_from_flatten_keys(input2)
    input_data = {
        "request": input3
    }
    input_data = dict_utils.to_str(input_data)
    
    url = f"{SVD_URL}/api/v3/requests/"
    headers ={"authtoken":AUTHTOKEN}
    data = {'input_data': input_data}
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.post(url,headers=headers,data=data,verify=False)
    object = json.loads(response.text)
    
    status = __parse_response_status(object)
    if log is not None:
        log["code"] = status["code"]
        log["messages"] = status["messages"]

    if status["code"] == 0:
        request_id = object["request"]["id"]
        return request_id
    return None
    

def __get_detail_note(request_id,note_id,log=None):
    url = f"{SVD_URL}/api/v3/requests/{request_id}/notes/{note_id}"
    headers ={"authtoken":AUTHTOKEN}
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.get(url,headers=headers,verify=False)
    object = json.loads(response.text)
    status = __parse_response_status(object)

    if log is not None:
        log["code"] = status["code"]
        log["messages"] = status["messages"]

    if status["code"] == 0:
        note = object["note"]
        note = {"description":note["description"]}
        return note
    return None

def all_request_notes(request_id,log = None):
    outputs = []
    url = f"{SVD_URL}/api/v3/requests/{request_id}/notes"
    headers ={"authtoken":AUTHTOKEN}
    input_data = '''{
        "list_info": {
            "row_count": 20,
            "start_index": 1,
            "sort_field": "added_time",
            "sort_order": "desc",
            "get_total_count": true
        }
    }'''
    params = {'input_data': input_data}
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.get(url,headers=headers,params=params,verify=False)
    object = json.loads(response.text)
    #pprint.pprint(object)
    status = __parse_response_status(object)

    if log is not None:
        log["code"] = status["code"]
        log["messages"] = status["messages"]

    if status["code"] == 0:
        notes = object["notes"]
        if len(notes) == 0:
            return outputs          
        else:
            for note in notes:
                note_id = note["id"]
                note_log = {}
                note = __get_detail_note(request_id,note_id,note_log)

                if note_log["code"] == 0:
                    outputs.append(note)
                else:
                    if log is not None:
                        log["code"] = note_log["code"]
                        log["messages"] = note_log["messages"]
                        return None
    return outputs           

def add_request_note(request_id, description, log=None):
    url = f"{SVD_URL}/api/v3/requests/{request_id}/notes"
    headers = {"authtoken": AUTHTOKEN}
    note_payload = {
        "note": {
            "description": description,
            "show_to_requester": True,
            "mark_first_response": False,
            "add_to_linked_requests": True
        }
    }
    input_data = json.dumps(note_payload, ensure_ascii=False)
    data = {'input_data': input_data}
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.post(url, headers=headers, data=data, verify=False)
    object = json.loads(response.text)
    #pprint.pprint(object)    
    status = __parse_response_status(object)

    if log is not None:
        log["code"] = status["code"]
        log["messages"] = status["messages"]

    if status["code"] == 0:
        return True
    return False

def close_request(id, comments, log=None):
    url = f"{SVD_URL}/api/v3/requests/{id}/close"
    headers = {"authtoken": AUTHTOKEN}
    closure_payload = {
        "request": {
            "closure_info": {
                "requester_ack_resolution": True,
                "requester_ack_comments": comments,
                "closure_comments": comments,
                "closure_code": {
                    "name": "success"
                }
            }
        }
    }
    input_data = json.dumps(closure_payload, ensure_ascii=False)
    data = {'input_data': input_data}
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.put(url, headers=headers, data=data, verify=False)
    object = json.loads(response.text)
    status = __parse_response_status(object)
    if log is not None:
        log["code"] = status["code"]
        log["messages"] = status["messages"]
    if status["code"] == 0:
        return True
    return False

#thời gian tính yêu cầu từ servicedesk (từ 8h sáng - 17h chiều)
#riêng thứ 7 (từ 8h sáng - 12h trưa); chủ nhật nghỉ không tính                
def compute_remaining_seconds(due_by_time, now = None):
    if not now:
        now = date_utils.get_current_time()
        
    #thời gian now rơi vào các khoản thời gian nghỉ (sau giờ làm việc) => lùi về trước khi kết thúc thời gian làm việc (đồng bộ cách tính)    
    if date_utils.get_weekday(now) == date_utils.SATURDAY and date_utils.get_hour(now) >= 12:
        now = date_utils.set(now, hour = 12, minute = 0)
    elif date_utils.get_weekday(now) < date_utils.SATURDAY and date_utils.get_hour(now) >= 17:
        now = date_utils.set(now, hour = 17, minute = 0)   
    elif date_utils.get_weekday(now) == date_utils.SUNDAY:        
        now = date_utils.set(now, day = date_utils.get_day(now)-1, hour = 12, minute = 0)   
        
    between_info = date_utils.date_between(due_by_time, now)
    remaining_minutes = between_info["num_minutes"] - 15*between_info["num_days"]*60
    if date_utils.has_weekday(now,due_by_time, date_utils.SATURDAY):
        remaining_minutes -= 5*60 #thời gian chiều thứ 7
    if date_utils.has_weekday(now, due_by_time, date_utils.SUNDAY):
        remaining_minutes -= 9*60 #thời gian chủ nhật
    
    return remaining_minutes*60

def parse_description(description):
    description = string_utils.remove_html_tags(description, exceptions = ["table"])
    conversations = description.split("From:")
    if len(conversations) > 0:
        main = conversations[0]
        conversations.reverse()
        for i in range(len(conversations)-1):
            conversations[i] = f"Hội thoại {i+1}:\nFrom:{conversations[i]}"
        return {
            "main": main,
            "conversations": conversations
        }
    else:     
        return {
            "main": description,
            "conversations": []
        }        
    

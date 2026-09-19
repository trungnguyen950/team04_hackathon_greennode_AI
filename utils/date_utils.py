#lasted update: 20/1/2026
from datetime import datetime, timedelta, timezone
from datetime import time as dtime
import time
import pytz

MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6

ENGLISH_MONTHS = {
    'January' : 1,
    'February' : 2,
    'March' : 3,
    'April' : 4,
    'May' : 5,
    'June' : 6,
    'July' : 7,
    'August' : 8,
    'September' : 9,
    'October' : 10,
    'November' : 11,
    'December' : 12
}

#lấy tổng giờ
#note: dùng khi lấy d2-d1 nên ra ít giờ, không lấy từ date thực tế
def get_hours_total(deltatime):
    return deltatime.total_seconds() / 3600 # 1 giờ = 3600 giây

def format_timedelta(delta, deltatime_format = "{hours:02} giờ {minutes:02} phút {seconds:02} giây"):
    if "{days}" in deltatime_format:
        # Trích xuất số ngày
        days = delta.days
        # Tính số giờ, phút và giây từ phần còn lại của timedelta
        hours, remainder = divmod(delta.seconds, 3600)  # chia cho 3600 để có giờ
        minutes, seconds = divmod(remainder, 60)  # chia còn lại cho 60 để có phút

        # Định dạng thành chuỗi theo dạng "giờ:phút:giây"
        return deltatime_format.format(days = days, hours = hours, minutes = minutes, seconds = seconds)    
    else: #nếu không dùng {days} thì {hours} sẽ cộng thêm 24 giờ 1 ngày
        # Trích xuất số ngày và chuyển đổi thành giờ
        day_hours = delta.days * 24        
        # Tính số giờ tổng cộng (bao gồm cả ngày)
        hours = day_hours + delta.seconds // 3600
        # Tính số phút và giây còn lại từ phần giây
        minutes, seconds = divmod(delta.seconds % 3600, 60)
    
        # Định dạng thành chuỗi theo dạng "giờ:phút:giây"
        return deltatime_format.format(hours = hours, minutes = minutes, seconds = seconds)

#class deltatime cho biết khoản thời gian 
#ví dụ: thi chạy tổ chức trong 1 giờ. biểu diển 1 giờ bằng deltatime
def create_deltatime(total_seconds):
    return timedelta(seconds=total_seconds)

def get_year(datetime):
    return datetime.year

def get_month(datetime):
    return datetime.month

def get_day(datetime):
    return datetime.day

def get_minute(datetime):
    return datetime.minute

def get_second(datetime):
    return datetime.second

def get_hour(datetime):
    return datetime.hour    

def get_current_time():
    milli = round(time.time() * 1000)
    return datetime.fromtimestamp(milli / 1000)

#0h sáng
def get_start_of_day(time):
    return set(time, hour = 0, minute = 0, second=0, microsecond=0)

#12h đêm
def get_end_of_day(time):
    return set(time, hour = 23, minute = 59, second=59, microsecond=999999)
    

#lấy thứ (ví dụ thứ) của ngày
#return 0 = Thứ 2, 1 = Thứ 3, ..., 6 = Chủ nhật
def get_weekday(datetime):
    return datetime.weekday()    

#kiểm tra giữa 2 thời gian có thứ nào đó không (vd thứ 7, chủ nhật)
def has_weekday(start_date, end_date, target_weekday):
    current = start_date
    while current <= end_date:
        if current.weekday() == target_weekday:
            return True
        current += timedelta(days=1)
    return False

def next_weekday(start_date, target_weekday):
    days_ahead = target_weekday - get_weekday(start_date)
    if days_ahead <= 0:
        days_ahead += 7
    return add(start_date,num_days=days_ahead)

#đếm từ d1 tới d2 đã mấy lần đi qua target_time
#d1: 16h 19/11 -> d2: 8h 21/11, target_time: 21h 
#output: 2 (2 lần đi qua 21h là 21h 19/11 và 21h 20/11)
def count_cross_times(d1, d2, target_time: time):
    # Bảo đảm d1 <= d2
    if d1 > d2:
        d1, d2 = d2, d1

    # Lần target_time đầu tiên trong ngày sau d1
    first = datetime.combine(d1.date(), target_time)
    if first <= d1:
        first += timedelta(days=1)

    # Nếu thời điểm này nằm sau d2 → không qua lần nào
    if first > d2:
        return 0

    # Tổng số lần target_time lặp lại mỗi ngày
    diff_days = (d2 - first).days
    return diff_days + 1

#khoản thời gian cách nhau giữa d1 và d2; hours và minutes tính tổng; còn ngày thì qua 12h đêm là tính 1 ngày 
#ví dụ 1: 16h chiều 19/11 tới 8 sáng 20/11 -> 16 giờ giây ...; 1 ngày
#ví dụ 2: 16h chiều 19/11 tới 8 sáng 21/11 -> 40 giờ giây ...; 2 ngày
def date_between(d1, d2):
    dif = d2 - d1
    # Lấy giá trị tuyệt đối
    dif = abs(dif)

    total_minutes = int(dif.total_seconds() // 60)
    total_hours = int(dif.total_seconds() // 3600)

    # THAY vì số ngày → trả về số lần đi qua 0h đêm (qua ngày mới)
    num_cross = count_cross_times(d1, d2, dtime(0,0))

    return {
        "num_days": num_cross,
        "num_hours": total_hours,
        "num_minutes": total_minutes
    }

def now():
    utc0 = timezone(timedelta(hours=0))
    date_utc0 = datetime.now(utc0)
    date_utc7 = add(date_utc0,num_hours=7)
    return date_utc7
    
def substract(date, num_days = 0, num_hours = 0, num_minutes = 0, num_seconds = 0):
    return date - timedelta(days = num_days, hours= num_hours, minutes = num_minutes, seconds = num_seconds)

def add(date, num_days = 0, num_hours = 0, num_minutes = 0, num_seconds = 0):
    return date + timedelta(days = num_days, hours= num_hours, minutes = num_minutes, seconds = num_seconds)

#year = 2000,month = 12, hour = 24, minute = 60, second = 60, microsecond = 9999999999
def set(date, **arg):
    new_date = date.replace(**arg)
    return new_date

#Date Utils
#%d/%m/%Y -> 11/01/2018
#%d/%m/%Y %H:%M:%S -> 10/11/2022  9:50:41
#%Y-%m-%d %H:%M:%S,%f -> 2025-12-05 15:03:04,336
#%d/%m/%Y %H:%M:%S %p -> 10/11/2022  9:50:41 PM (Nếu PM thì phải +12h)
#%Y%m%d%H%M%S.%f -> 20230704233217.000000 (từ poweshell/sccm)
def convertStr2Date(date_str,format_str='%d/%m/%Y'):
    if format_str == "%Y%m%d%H%M%S.%f" and date_str.endswith("+***"):
        date_str = date_str[:-4]
    date_obj =  datetime.strptime(date_str, format_str)
    if '%p' in format_str and "PM" in date_str:
        date_obj += timedelta(hours=12)        
    return date_obj

def convertDate2Str(date_obj,format_str='%d/%m/%Y'):
    if '%p' in format_str and date_obj.hour > 12:
       date_obj -= timedelta(hours=12)
       return date_obj.strftime(format_str).replace('AM','PM')
    return date_obj.strftime(format_str)

#unix time = "1768881313569" => '20/01/2026 10:55 AM'
def convertUnixTimeStamp2Date(unix_timestamp):
    VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
    return datetime.fromtimestamp(unix_timestamp/1000,VN_TZ)

def convertDate2UnixTimeStamp(date) -> int:
    VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
    try:
        date = VN_TZ.localize(date)
    except:
        pass
    return int(date.timestamp() * 1000)    

def show_difference_from_now(date):
    current_time = get_current_time()
    diff = date_between(date,current_time)
    if (diff["num_days"] > 0):
        return str(diff["num_days"]) + " ngày trước"
    elif (diff["num_hours"] > 0):
        return str(diff["num_hours"]) + " giờ trước"
    elif (diff["num_minutes"] > 0):
        return str(diff["num_minutes"]) + " phút trước"

def parse_month_year_format(monthyear_str):
    separater_index = monthyear_str.index(' ')

    if len(separater_index) != 2:
        return None
        
    firstPart = monthyear_str[0:separater_index]
    secondPart = monthyear_str[separater_index+1: len(monthyear_str)]

    if firstPart not in ENGLISH_MONTHS:
        return None

    return {'month':ENGLISH_MONTHS[firstPart], 'year':int(secondPart)}    
    
def parse_day_month_year_format(daymonthyear_str):
    parts = daymonthyear_str.split("/")
        
    if len(parts) != 3:
        return None     
        
    return {'day': int(parts[0]), 'month':int(parts[1]), 'year':int(parts[2])}

def parse_date_range(str): 
    parts = str.split("-")
        
    if len(parts) != 2:
        return None     
        
    start_date = parse_day_month_year_format(parts[0].strip())
    end_date = parse_day_month_year_format(parts[1].strip())

    if not start_date or not end_date: 
        return None
            
    return {'start_date': start_date, 'end_date': end_date}

#20220725212231.000000+420 => 25/07/2022
def parse_computer_format(str):
    if len(str) > 7:
        str = str[0:8]
        return convertStr2Date(str,"%Y%m%d")
    return None
    

#compare: không dùng trực tiếp phép toán <,>,= do vấn đề offset-naive and offset-aware datetimes
def compare_dates(date1: datetime, date2: datetime, method: str) -> bool:
    # Chuyển cả hai về naive datetime để tránh lỗi so sánh
    if date1.tzinfo is not None:
        date1 = date1.replace(tzinfo=None)
    if date2.tzinfo is not None:
        date2 = date2.replace(tzinfo=None)

    if method == "==":
        return date1 == date2
    elif method == "!=":
        return date1 != date2
    elif method == ">":
        return date1 > date2
    elif method == "<":
        return date1 < date2
    elif method == ">=":
        return date1 >= date2
    elif method == "<=":
        return date1 <= date2
    else:
        raise ValueError(f"Phép so sánh không hợp lệ: {method}")    

#compare: không dùng trực tiếp phép toán - do vấn đề offset-naive and offset-aware datetimes
def subtract_dates(date1: datetime, date2: datetime) -> bool:
    # Chuyển cả hai về naive datetime để tránh lỗi thực hiện phép toán
    if date1.tzinfo is not None:
        date1 = date1.replace(tzinfo=None)
    if date2.tzinfo is not None:
        date2 = date2.replace(tzinfo=None)
    return date1-date2

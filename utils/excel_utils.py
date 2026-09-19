#lasted update: 25/6/2026

from openpyxl import Workbook, load_workbook #pip install openpyxl
from openpyxl.styles import Alignment
from copy import copy
import os
try:
    import win32com.client
    import win32com
except ImportError:
    win32com = None

class Excel_Table:    
    single_charater_index_mapping = None
    table = None
    label = None
    row_start = 0
    row_end = None
    col_start = 0
    col_end = None
    ws = None

    #PRIVATE
    def __get_column_length(self):
        column_length = 1
        if self.label:
            column_length = len(self.label)
        if len(self.table) > 0:
            column_length = len(self.table[0])
        return column_length

    def __format_cell_value(self,value):
        # nếu là list → gộp thành nhiều dòng trong 1 cell
        if isinstance(value, list):
            cell_value = "\n".join(str(v) for v in value)
        else:
            cell_value = "" if value is None else str(value)
        return cell_value

    def __insert_row_at(self, index, data = None):
        """
        Chèn một dòng mới vào worksheet và giữ nguyên format
        của dòng phía trên.
    
        Args:
            ws: openpyxl Worksheet
            row_index: vị trí dòng cần chèn
            data: list dữ liệu ghi vào dòng mới
        """
        if data:
            self.table.insert(index,data)            

        # Chèn dòng mới
        ws_index = index+self.row_start
        if self.table:
            ws_index += 1
        self.ws.insert_rows(ws_index)
    
        # Copy style từ dòng phía trên
        source_row = ws_index - 1
    
        if source_row > 0:
            for col in range(1, self.ws.max_column + 1):
                source_cell = self.ws.cell(source_row, col)
                target_cell = self.ws.cell(ws_index, col)
    
                if source_cell.has_style:
                    target_cell._style = copy(source_cell._style)
    
                target_cell.font = copy(source_cell.font)
                target_cell.fill = copy(source_cell.fill)
                target_cell.border = copy(source_cell.border)
                target_cell.alignment = copy(source_cell.alignment)
                target_cell.protection = copy(source_cell.protection)
                target_cell.number_format = copy(source_cell.number_format)
    
        # Ghi dữ liệu
        if data:
            for col, value in enumerate(data, start=1):
                self.ws.cell(row=ws_index, column=col, value=self.__format_cell_value(value))

    def __insert_column_at(self, index, data = [], column_label = None):
        """
        Chèn một cột mới vào worksheet và giữ format
        của cột bên trái.
    
        Args:
            ws: openpyxl Worksheet
            col_index: vị trí cột cần chèn (1 = A)
            data: list dữ liệu theo từng dòng
        """

        for i, row in enumerate(self.table):
            if data and i < len(data):
                row.insert(index,data[i])
            else:
                row.insert(index,"")
    
        # Chèn cột mới
        ws_index = index+self.col_start
        self.ws.insert_cols(ws_index)
    
        # Cột nguồn để copy format (cột bên trái)
        source_col = ws_index - 1
    
        if source_col > 0:
            for row in range(1, self.ws.max_row + 1):
                source_cell = self.ws.cell(row=row, column=source_col)
                target_cell = self.ws.cell(row=row, column=ws_index)
    
                if source_cell.has_style:
                    target_cell._style = copy(source_cell._style)
    
                target_cell.font = copy(source_cell.font)
                target_cell.fill = copy(source_cell.fill)
                target_cell.border = copy(source_cell.border)
                target_cell.alignment = copy(source_cell.alignment)
                target_cell.protection = copy(source_cell.protection)
                target_cell.number_format = copy(source_cell.number_format)
    
        # Ghi dữ liệu vào cột mới
        if data:
            row_start = self.row_start
            if column_label:
                self.ws.cell(row=row_start, column=ws_index, value=column_label)
                row_start += 1
                
            for row, value in enumerate(data, start=row_start):
                self.ws.cell(row=row, column=ws_index, value=self.__format_cell_value(value))
        
    #xóa tất cả dòng mà tất ô là None
    def __remove_null_rows(self):
        self.table = [row for row in self.table if not all(x is None for x in row)]

    def init_chararer_index_mapping():
        single_charater_index_mapping = {}
        characters = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
        num = 0
        for i in range(len(characters)):
            num += 1
            single_charater_index_mapping[characters[i]] = num
        for i in range(len(characters)):
            for j in range(len(characters)):
                num += 1
                single_charater_index_mapping[characters[i]+characters[j]] = num
        return single_charater_index_mapping
    
    #"row_end = None" không xác định số dòng 
    def __init__(self, worksheet, row_start, col_start, row_end, col_end, has_label = False):
        #init oject params
        self.single_charater_index_mapping = Excel_Table.init_chararer_index_mapping()
        self.table = []
        self.ws = worksheet
        
        #convert input params
        row_start = int(row_start)
        if row_end:
            row_end = int(row_end)
        col_start = self.single_charater_index_mapping[col_start]
        col_end = self.single_charater_index_mapping[col_end]
        
        i = 0
        for row in worksheet.values:
            i += 1
            if row_start <= i and (not row_end or i <= row_end):
                table_row = []
                j = 0
                for value in row:
                    j += 1
                    if col_start <= j and j <= col_end:
                        table_row.append(value)
                self.table.append(table_row)
        
        if has_label:
           self.label = self.table[0]
           del self.table[0]

        self.row_start = row_start
        self.row_end = j
        self.col_start = col_start
        self.col_end = col_end


        self.__remove_null_rows()
        #print(self.label)
        #print(self.table)

    def update_cell(self, row_index, col_index, value):
        self.table[row_index][col_index] = value
        if self.label:
            self.ws.cell(row_index+self.row_start+1, col_index+self.col_start, self.__format_cell_value(value))
        else:
            self.ws.cell(row_index+self.row_start, col_index+self.col_start, self.__format_cell_value(value))
            
    def get_column_index(self, column_char = None, label = None):
        column_index = -1
        if label and self.label and label in self.label:
            column_index = self.label.index(label)
            #print(label)
            #print(self.label.index(label))
        if column_char:
            if column_char in self.single_charater_index_mapping:
                column_index = self.single_charater_index_mapping[column_char]
                if self.col_start <= column_index and column_index <= self.col_end:
                    column_index = column_index - self.col_start + 1
        return column_index
        
    def get_column(self, column_char = None, label = None):
        columns = []        
        column_index = self.get_column_index(column_char,label)
        if column_index > -1:
            for row in self.table:
                columns.append(row[column_index])
        return columns    

    def get_row(self, row_index):
        if row_index >= 0 and row_index < len(self.table):
            return self.table[row_index]
        return None

    def get_last_row(self):
        length = self.get_row_length()
        if length > 0:
            return self.table[length-1]

    def get_row_length(self):
        return len(self.table)

    def update_row(self, row_index, data):
        for i,value in enumerate(data):
            self.update_cell(row_index, i, value)

    def remove_row(self, row_index = None, row = None):
        if row_index is not None:
            self.table.pop(row_index)
            if self.label:
                print(row_index+self.row_start+1)
                self.ws.delete_rows(row_index+self.row_start+1, amount=1)
            else:
                self.ws.delete_rows(row_index+self.row_start, amount=1)                
        if row:
            pos = self.table.index(row) if row in self.table else None
            self.table.remove(row)
            if pos:
                if self.label:
                    self.ws.delete_rows(pos+self.row_start+1, amount=1)  
                else:
                    self.ws.delete_rows(pos+self.row_start, amount=1)
        self.row_end -= 1
        
    def remove_rows(self, rows):
        for row in rows:
            self.remove_row(row = row)

    def insert_row(self, data = None, row_before = None, first = None, last = None):
        column_length = self.__get_column_length()
        new_row = [""] * column_length
        if data:
            for i in range(len(data)):
                if i < column_length:
                    new_row[i] = data[i]
                    
        if first:
            row_index = 0
        elif last:
            row_index = len(self.table)
        elif row_before:
            row_index = self.table.index(row_before)+1         
        self.__insert_row_at(row_index, new_row)
        self.row_end += 1
            
        return new_row
            
    def insert_column(self, data = None, column_char_before = None, column_label_before = None, first = None, last = None, column_label = None):
        index = -1
        if first:            
            index = 0
        elif last:
            column_length = self.__get_column_length()            
            index = column_length
        else:
            column_index = self.get_column_index(column_char_before,column_label_before)
            if column_index > -1:
                index = column_index+1
        
        if index >= 0:
            self.__insert_column_at(index, data, column_label = column_label)
            self.col_end += 1
            if self.label and column_label:
                self.label.insert(index,column_label)
        return
    
    def remove_column(self, column_char = None, column_label = None):
        column_index = self.get_column_index(column_char,column_label)
        if column_index > -1:
            for row in self.table:
                row.pop(column_index)
            self.ws.delete_cols(column_index+self.col_start, amount=1)
            self.col_end -= 1

    def update_column(self, column_values, column_char = None, column_label = None):
        column_index = self.get_column_index(column_char,column_label)
        if column_index > -1:
            for i in range(0,len(self.table)):
                self.update_cell(i, column_index, column_values[i])  

    #chỉ dành cho table có label
    #obj = {"column label 1":"value","column label 2":"value",...}
    #điều kiện: label phải duy nhất không trùng hay None
    def get_object_list(self, log = None):
        if self.label:
            #kiểm tra label không phải duy nhất và khác None
            if not(all(item is not None for item in self.label) and len(self.label) == len(set(self.label))):
                if log is not None:
                    log["code"] = 302
                    log["messages"] = ["Danh sách label bị trùng hay None"]
                return []
            object_list = []
            for row in self.table:
                obj = {}              
                for i, item in enumerate(self.label):
                    obj[item] = row[i]
                object_list.append(obj)
            return object_list
        else:
            return []

def get_worksheet(wb, sheet_name):
    for i in range(0,len(wb.sheetnames)):
        if wb.sheetnames[i] == sheet_name:
            return wb.worksheets[i]
    return None

#override = False: chỉ fill vô empty space
def lookup(source_map_column = None, source_fill_column = None, target_map_column = None, target_fill_column = None, override = False):
    source_dict = {}
    
    #print(source_map_column)
    #print(source_fill_column)
    
    for i in range(0,len(source_map_column)):
        if source_map_column[i] and source_fill_column[i]:
            if source_map_column[i] not in source_dict:
                source_dict[source_map_column[i]] = source_fill_column[i]
    
    for j in range(0,len(target_fill_column)):
        if override and target_map_column[j] in source_dict:
            target_fill_column[j] = source_dict[target_map_column[j]]
        elif not override and not target_fill_column[j] and target_map_column[j] in source_dict:
            target_fill_column[j] = source_dict[target_map_column[j]]   
            
def read(filename):
    wb = load_workbook(filename)
    return wb

def close(file_path, save_change):
    if win32com is None:
        return
    try:
        normalize_file_path = os.path.normcase(os.path.abspath(file_path))
        excel = win32com.client.GetObject(Class="Excel.Application")
        for wb in excel.Workbooks:
            normalize = os.path.normcase(os.path.abspath(wb.FullName))
            if normalize == normalize_file_path:
                wb.Close(SaveChanges=save_change)
                if excel.Workbooks.Count == 0:
                    excel.Quit()
    except:
        pass

#force: tắt process hiện tại để có thể write dc
def write(workbook, file_path, force = False, save_change = False):
    if force:
        close(file_path,save_change)
    workbook.save(filename = file_path)
    return True

def create_simple_file(title, dsLabel, dsItem): 
    wb = Workbook()

    ws1 = wb.active
    ws1.title = "Sheet 1"
    ws1['A1'] = title
    
    for col in range(1, len(dsLabel)+1):
        _ = ws1.cell(column=col, row=2, value=dsLabel[col-1])

    # data
    for i in range(len(dsItem)):
        item = dsItem[i]
        for j in range(len(item)):
            value = item[j]
            
            # nếu là list → gộp thành nhiều dòng trong 1 cell
            if isinstance(value, list):
                cell_value = "\n".join(str(v) for v in value)
            else:
                cell_value = "" if value is None else str(value)
            
            cell = ws1.cell(
                column=j + 1,
                row=i + 3,
                value=cell_value
            )
    
            # bật wrap text để thấy xuống dòng
            cell.alignment = Alignment(wrap_text=True)
    return wb


def create_simple_file2(title, dsLabel, dsObject, label_map = {}):
    wb = Workbook()

    ws1 = wb.active
    ws1.title = "Sheet 1"
    ws1['A1'] = title
    
    for col in range(1, len(dsLabel)+1):
        label = dsLabel[col-1]
        if label_map and label in label_map:
            _ = ws1.cell(column=col, row=2, value=label_map[dsLabel[col-1]])
        else:
            _ = ws1.cell(column=col, row=2, value=dsLabel[col-1])

    for i in range(len(dsObject)):
        obj = dsObject[i]
        for j, label in enumerate(dsLabel):
            value = obj.get(label)
    
            # nếu là list → gộp thành nhiều dòng trong 1 cell
            if isinstance(value, list):
                cell_value = "\n".join(str(v) for v in value)
            else:
                cell_value = "" if value is None else str(value)
    
            cell = ws1.cell(
                column=j + 1,
                row=i + 3,
                value=cell_value
            )
    
            # bật wrap text để thấy xuống dòng
            cell.alignment = Alignment(wrap_text=True)
    return wb
    
def create_simple_sheet(wb, sheet_name, index, title = None, labels = [], items = [], auto_alignment = True):
    ws = wb.create_sheet(sheet_name, index)
    start = 0
    if title:
        ws['A1'] = title
        start = 1    

    if labels:
        for col in range(1, len(labels)+1):
            _ = ws.cell(column=col, row=1+start, value=labels[col-1])
        start += 1

    # data
    for i in range(len(items)):
        item = items[i]
        for j in range(len(item)):
            value = item[j]
            
            # nếu là list → gộp thành nhiều dòng trong 1 cell
            if isinstance(value, list):
                cell_value = "\n".join(str(v) for v in value)
            else:
                cell_value = "" if value is None else str(value)
            
            cell = ws.cell(
                column=j + 1,
                row=i + start+1,
                value=cell_value
            )
    
            # bật wrap text để thấy xuống dòng
            if auto_alignment:
                cell.alignment = Alignment(wrap_text=True)
    return ws

def excel_to_matrix(file_path, sheet_name=None):
    wb = load_workbook(file_path, data_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active

    matrix = []
    for row in ws.iter_rows(values_only=True):
        matrix.append(list(row))
    return matrix

def autofit(worksheet, min_width=8, max_width=50):
    for col_cells in worksheet.columns:
        max_length = 0
        column_letter = col_cells[0].column_letter

        for cell in col_cells:
            value = cell.value

            if value is None:
                continue

            text = str(value)

            # nếu có xuống dòng → bật wrap_text
            if "\n" in text:
                cell.alignment = Alignment(
                    wrap_text=True,
                    vertical="top"
                )

                # lấy dòng dài nhất trong cell
                longest_line = max(text.split("\n"), key=len)
                length = len(longest_line)
            else:
                length = len(text)

            max_length = max(max_length, length)

        # set width có giới hạn
        adjusted_width = max(min_width, min(max_length + 2, max_width))
        worksheet.column_dimensions[column_letter].width = adjusted_width

def find_worksheet(workbook, worksheet_name):
    if worksheet_name not in workbook.sheetnames:
        raise ValueError(f"Sheet '{worksheet_name}' không tồn tại trong workbook")
    return workbook[worksheet_name]

def all_worksheet_names(workbook):
    return workbook.sheetnames

def remove_worksheet(workbook,worksheet):
    workbook.remove(worksheet)
    
def create_new_workbook():
    return Workbook()    
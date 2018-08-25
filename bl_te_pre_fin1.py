# Import all the libraries
import os, re, sys, pytesseract, argparse, cv2, imutils, json
from PIL import Image
import numpy as np
from collections import OrderedDict
from operator import itemgetter

# Configure pytesseract 4.0.0 beta version path 
tessdata_dir_config = '--tessdata-dir "C:/Program Files (x86)/Tesseract-OCR_beta/tessdata"'
pytesseract.pytesseract.osd_to_dict="C:/Program Files (x86)/Tesseract-OCR_beta/tessdata"
pytesseract.pytesseract.tesseract_cmd = 'C:/Program Files (x86)/Tesseract-OCR_beta/ta400b'

# Get the image path
img_name = "t2.jpg"

# Call pytesseract to get strings from the image
text = pytesseract.image_to_string(Image.open(img_name),lang='eng', config=tessdata_dir_config)

# Declare text file name for writing the string lines in that
txt_file_name = img_name[:-4]+".txt"

# Open the text file and write the strings obtained by pytesseract
f = open(txt_file_name, "w",encoding='utf-8')
f.write(text)
f.close()

# Open the text file and read between lines and have them in a list
with open(txt_file_name,encoding="utf8") as f:
    content = f.readlines()

# Define a function to check whether a string is a number - int/float whatever
def chk_nm_flt(n):
    try:
        float(n)   # Type-casting the string to `float`.
                   # If string is not a valid `float`, 
                   # it'll raise `ValueError` exception
    except ValueError:
        return False
    return True

# Declare prelim variables before list of assets & liabilities (as in final json) as null
business_name = "null"
business_owner = "null"
address = "null"
date_of_birth = "null"
pan_no = "null"
balance_sheet_date = "null"
prepared_date = "null"
prepared_place = "null"
prepared_by = "null"



# Get the value of the prelim variables
# Iterate through the lines of the 
for i in content:
	# Check business name
	# Pytesseract sometimes read "M/S" in the image as "MIS"
	if "M/S" in i or "MIS" in i:
		business_name = i[4:].replace("\n","")

	# Check business owner
	if "Prop:" in i:
		business_owner = i.split(":")[1].replace("-","").replace("- ","").replace("\n","")

	# Check pan number
	if "PAN" in i:
		pan_no = i.split(":")[1].replace("- ","").replace("\n","").replace(".","")
		# We can also use regular expression to find pan number 
		# pan_no = re.search(r'[A-Za-z]{5}[0-9]{4}[A-Za-z]',i).group()

	# Check date of birth
	if "Birth" in i:
		date_of_birth_find = re.search(r'(\d+/\d+/\d{4})',i)
		if date_of_birth_find:
			date_of_birth = date_of_birth_find.group()

	# Check address
	if "AT:" in i or "At:" in i:
		address = i.split(":")[1].replace("\n","")

	# Check balance sheet date
	if "AS ON" in i or "AS AT" in i:
		if "YEAR ENDED" in i:
			bal_sht_date_find = re.search(r'YEAR ENDED ',i)
			bal_sht_date = i[bal_sht_date_find.span()[1]:].replace("\n","")
		else:
			bal_sht_date_find = re.search(r'AS ',i)
			bal_sht_date = i[bal_sht_date_find.span()[1]+3:].replace("\n","")

	# We would check the prepared_date, prepared_place, prepared_by at the bottom part

# Check from which line the table starts
for i in content:
	if "AMOUNT" in i or "Amount" in i:
		table_head_line_no = content.index(i)
print(table_head_line_no)

# Declare lists - one for liability items, one for asset items, one for rupees amounts, one for whole line
liability_items = [] 
asset_items = []
floating_numerics = []
whole_line_list = []

# Declare the asset and liabilities keywords for checking and safe appending in lists
asset_keywords = ["Dep", "Stock in Trade", "Advance", "Debtors", "FD", "Current A", "Bank Bal", "Cash", "Fixed A", "FIXED A", "Investment" , "INVESTMENT"]
liability_keywords = ["Opening B", "OPENING B", "Drawings", "Income", "Secured L", "Loan", "LOAN", "Current L", "CURRENT L", "Payable", "Creditors"]

# Cleanse the line content removing underscores
for i in content[table_head_line_no + 1:]:
	index_i = content.index(i)
	new_i = i.replace("_", " ")
	content.remove(i)
	content[index_i:index_i] = [new_i] 

# Cleanse the line content removing vertical bars
for i in content[table_head_line_no + 1:]:
	index_i = content.index(i)
	new_i = i.replace("|", " ")
	content.remove(i)
	content[index_i:index_i] = [new_i] 

# Cleanse the line content removing opening third brackets
for i in content[table_head_line_no + 1:]:
	index_i = content.index(i)
	new_i = i.replace("[", " ")
	content.remove(i)
	content[index_i:index_i] = [new_i] 

# Cleanse the line content removing backslashes
for i in content[table_head_line_no + 1:]:
	index_i = content.index(i)
	new_i = i.replace("\\", " ")
	content.remove(i)
	content[index_i:index_i] = [new_i] 

# Declare three string variables
first_string = ''
middle_string = ''
last_string = ''

# Declare two lists with liability and asset headings
liability_heads = ["Opening B", "OPENING B", "Loan", "LOAN","Current L", "CURRENT L"]
asset_heads = ["Fixed A", "FIXED A", "Investment", "INVESTMENT", "Current A","CURRENT A", "Bank B", "BANK B"]

# Declare a dictionary to save the lines where there is no numeric and contain liability or asset heads
# The dictionary would contain heads as keys and next line first floating numeric as values
heads_no_num = {}
# Go through all the table lines starting from the position of table headline 
for i in content[table_head_line_no+1:]:
	print(i)
	# Get all the floating numeric values in a list from a line
	floating_numerics = re.findall(r'((?:\d+,+)+\d+\.\d{2})', i)
	print(floating_numerics)

	# If a line contains only strings and no floating numerics then they should be either liability head or asset head
	# However sometimes there may be some liability or asset items which aren't heads but aren't attached with any floating numeric 
	if len(floating_numerics) == 0 :
		# Check if they contain any liability headings
		for l_h in liability_heads:
			if l_h in i:
				liab_head_no_num = i
				# Get the number of line at which this liability head is
				liab_head_no_num_index = content.index(i)
				# Get the first floating numeric of the next line
				# Later we would find this floating numeric in the whole line list and introduce that liability head before that line

				liability_items.append([i])
				line_count_l = 1
				next_line_first_num_l = ''
				'''
				while True:
					next_line_first_num_l = re.findall(r'((?:\d+,+)+\d+\.\d{2})', content[liab_head_no_num_index+ line_count_l])
					line_count_l += 1
					heads_no_num[liab_head_no_num] = next_line_first_num_l
					if len(next_line_first_num_l) != 0 :
						break

				

				while len(re.findall(r'((?:\d+,+)+\d+\.\d{2})', content[liab_head_no_num_index + line_count_l])) != 0 :
					line_count_l += 1	
					next_line_first_num_l = re.findall(r'((?:\d+,+)+\d+\.\d{2})', content[liab_head_no_num_index+ line_count_l])[0]
					break
				heads_no_num[liab_head_no_num] = next_line_first_num_l
				'''

		# Check whether they contain any asset headings
		for a_h in asset_heads:
			if a_h in i:
				ast_head_no_num = i
				ast_head_no_num_index = content.index(i)

				asset_items.append([i])
				line_count_a = 1	
				next_line_first_num_a = ''
				
				'''
				while True:
					next_line_first_num_a = re.findall(r'((?:\d+,+)+\d+\.\d{2})', content[ast_head_no_num_index+ line_count_a])
					line_count_a += 1
					heads_no_num[ast_head_no_num] = next_line_first_num_a
					if len(next_line_first_num_a) != 0 :
						break
				
				while len(re.findall(r'((?:\d+,+)+\d+\.\d{2})', content[ast_head_no_num_index + line_count_a])) != 0 :
					next_line_first_num_a = re.findall(r'((?:\d+,+)+\d+\.\d{2})', content[ast_head_no_num_index+line_count_a])[0]
					line_count_a += 1
					break
				heads_no_num[ast_head_no_num] = next_line_first_num_a
				'''

	# Check if there are chunks of strings before the first element of floating numerics list 
	# If the floating numerics list has only one item then get the position of the item in the line 
	elif len(floating_numerics) == 1 :
		floating_numerics_item_pos = i.find(floating_numerics[0])
		print(floating_numerics_item_pos)
		# Get the length of the floating numerics item
		floating_numerics_item_len = len(floating_numerics[0])
		print(floating_numerics_item_len)
		# Get the chunks of string before the floating numerics item
		string_bfr_floating_numerics = i[:floating_numerics_item_pos]
		print(string_bfr_floating_numerics)
		# Get the chunks of string after the floating numerics item
		string_aftr_floating_numerics = i[floating_numerics_item_pos+floating_numerics_item_len:]
		print(string_aftr_floating_numerics)
		
		# There are three situations for having only one numeric in a line :
		# 1>	liability item ... liability amount ... asset item
		# 2>	liability item ... liability amount ... ' '
		# 3>	"THERE MAY BE SOME liability item"  ... asset item ... asset amount

		# If the chunk of strings after the numeric is not vacant : it is the first case
		if len(re.findall(r'\w',string_aftr_floating_numerics)) != 0:
			liability_items.append([string_bfr_floating_numerics, floating_numerics[0]])
			asset_items.append([string_aftr_floating_numerics])

		# If the chunk of strings after the numeric is vacant : this invokes the last two cases 
		if len(re.findall(r'\w',string_aftr_floating_numerics)) == 0:
			# For the last case, we need to check both for liability and asset keywords
			for a_k in asset_keywords:
				for l_k in liability_keywords:
					if a_k in string_bfr_floating_numerics and l_k in string_bfr_floating_numerics:
						# Divide this chunk of strings using double space as words inside either liability or asset items are separated by single spaces.
						temp_liab_ast_list = re.split(r'\s\s',string_bfr_floating_numerics)
						liability_items.append([temp_liab_ast_list[0]])
						asset_items.append([temp_liab_ast_list[0] if len(temp_liab_ast_list)==1 else temp_liab_ast_list[1], floating_numerics[0]])

					elif a_k in string_bfr_floating_numerics and l_k not in string_bfr_floating_numerics:
						asset_items.append([string_bfr_floating_numerics, floating_numerics[0]])
					elif a_k not in string_bfr_floating_numerics and l_k in string_bfr_floating_numerics:
						liability_items.append([string_bfr_floating_numerics, floating_numerics[0]]) 
			'''
			# Check with help of keywords whether these string chunks are asset or liability items
			for a_k in asset_keywords:
				if a_k in string_bfr_floating_numerics:
					liability_items.append([string_bfr_floating_numerics, floating_numerics[0]])

			for l_k in liability_keywords:
				if l_k in string_bfr_floating_numerics: 
					asset_items.append([string_aftr_floating_numerics, floating_numerics[0] ])

			'''
					

		# Append the chunk of strings and numeric in whole line list 
		whole_line_list.append([string_bfr_floating_numerics, floating_numerics[0],string_aftr_floating_numerics])
	
	elif len(floating_numerics) == 2:
		# Get the lengths and starting positions of the two numeric items 
		first_floating_item_pos = i.find(floating_numerics[0])
		first_floating_item_len = len(floating_numerics[0])
		second_floating_item_pos = i.find(floating_numerics[1])
		second_floating_item_len = len(floating_numerics[1])

		# Get three chunks of strings in between the two floating items
		first_string = i[:first_floating_item_pos]
		middle_string = i[first_floating_item_pos + first_floating_item_len:second_floating_item_pos]
		last_string = i[second_floating_item_pos + second_floating_item_len:]

		# If middle string contains some words, then first string is liability, middle one is asset items
		if len(re.findall(r'\w',middle_string)) != 0 :
			liability_items.append([first_string, floating_numerics[0]])
			asset_items.append([middle_string,floating_numerics[1]])

			whole_line_list.append([first_string,floating_numerics[0],middle_string,floating_numerics[1]])

		# If middle string contains no words, there can be two situations :
		# 1.The first string is in liability column, next two numerics are liability value and total value, last string may be in asset column
		# In the first case, last string must be asset item

		# 2.The first string is in asset column, next two numerics are asset value and total value
		# There may be that a liability item is mixed with the asset item
		elif len(re.findall(r'\w',middle_string)) == 0 and len(re.findall(r'\w',last_string)) == 0:
			# -----------------------NOT WORKING-----------------------
			# Check with keywords if the first string is liability item 
			for l_k in liability_keywords:
				if l_k in first_string:
					liability_items.append(first_string)

			# Check with keywords if the first string is asset item
			for a_k in asset_keywords:
				if a_k in middle_string:
					asset_items.append(first_string)

			whole_line_list.append([first_string,floating_numerics[0],floating_numerics[1]])

		elif len(re.findall(r'\w',middle_string)) == 0 and len(re.findall(r'\w',last_string)) != 0 :
			liability_items.append(first_string)
			asset_items.append(last_string)
			whole_line_list.append([first_string,floating_numerics[0],floating_numerics[1],last_string])


	elif len(floating_numerics) == 3:
		# If there are three floating numeric values in a line, there must be a vacant string between any two of them.
		# Get the lengths and starting positions of the three numeric items
		initial_floating_item_pos = i.find(floating_numerics[0])
		initial_floating_item_len = len(floating_numerics[0])
		middle_floating_item_pos = i.find(floating_numerics[1])
		middle_floating_item_len = len(floating_numerics[1])
		end_floating_item_pos = i.find(floating_numerics[2])
		end_floating_item_len = len(floating_numerics[2])

		# Get three chunks of strings in between the three floating numeric items.
		# Remember if there are three floating numeric items there won't be any string after the last one (as per balance sheet format).
		# Also note one of these three string must be vacant as we will get one from liability column and another from asset column 
		first_string = i[:initial_floating_item_pos]
		middle_string = i[initial_floating_item_pos + initial_floating_item_len : middle_floating_item_pos]
		last_string = i[middle_floating_item_pos + middle_floating_item_len : end_floating_item_pos]

		# If middle string contains no words : 
		# The initial string must be liability item
		# The end string must be asset item
		# In this case, the initial numeric is liability value, middle numeric is total liability value, end one is asset value
		# visual Format :
		# liability item ... liability value ... ' ' ... total liability value ... asset item ... asset value

		if len(re.findall(r'\w',middle_string)) == 0 :
			liability_items.append([first_string, floating_numerics[0], floating_numerics[1] ])
			asset_items.append([last_string , floating_numerics[2] ])

			whole_line_list.append([first_string,floating_numerics[0],floating_numerics[1],last_string,floating_numerics[2]])

		# If end string contains no words :
		# The initial string must be liability item 
		# The middle string must be asset item
		# In this case, the initial numeric is liability value, middle numeric is asset value, end numeric is total asset value
		# Visual Format :
		# liability item ... liability value ... asset item ... asset value ... total asset value ... ' ' 
		if len(re.findall(r'\w',last_string)) == 0 :
			liability_items.append([first_string, floating_numerics[0] ])
			asset_items.append([middle_string, floating_numerics[1], floating_numerics[2] ])

			whole_line_list.append([first_string,floating_numerics[0],middle_string,floating_numerics[1],floating_numerics[2]])


"""
# Append the line headings with no numeric into the whole line list
for i in whole_line_list:
	for j in i:
		for (k,v) in heads_no_num.items():
			# Check if the value of the dictionary of heads with no numeric matches with some items inside some element inside whole line list
			if v[0] in j:
				# Get the index of that item in the element of the whole line list
				buff_index = i.index(j)
				# Introduce the heads with no numeric at that position
				i[buff_index:buff_index] = [k] 
"""


# Create a dictionary with keys as headings and their position as values
ast_heads_dict = {}
liab_heads_dict = {}

# Create new lists for 

# Delete duplicate items in the list of asset items and liability items
asset_items_no_dupl = [ii for n,ii in enumerate(asset_items) if ii not in asset_items[:n]]
liability_items_no_dupl = [ii for n,ii in enumerate(liability_items) if ii not in liability_items[:n]]

# Check the main asset heading positions 
for i in asset_items_no_dupl:
	for j in i:
		# Check for asset headings
		if "Fixed A" or "FIXED A" in j:
			ast_heads_dict["fixed_asset"] = asset_items_no_dupl.index(i)
		if "Current A" or "CURRENT A" in j:
			ast_heads_dict["current_asset"] = asset_items_no_dupl.index(i)
		if "Investment" or "INVESTMENT" in j:
			ast_heads_dict["investment"] = asset_items_no_dupl.index(i)
		if "Bank B" or "BANK B" or "Cash" or "CASH" in j:
			ast_heads_dict["bank_balance"] = asset_items_no_dupl.index(i)

# Check the main liability heading positions 
for i in liability_items_no_dupl:
		# Check for liability headings
		if "Capital" or "CAPITAL" in j:
			liab_heads_dict["capital"] = liability_items_no_dupl.index(i)
		if "Secured L" or "SECURED L" or " Loan" or " LOAN" in j:
			liab_heads_dict["secured_loan"] = liability_items_no_dupl.index(i)
		if "Current L" or "CURRENT L" in j:
			liab_heads_dict["current_liabilities"] = liability_items_no_dupl.index(i)

print(liability_items_no_dupl)
print(asset_items_no_dupl)
print(heads_no_num)
print(whole_line_list)

print(ast_heads_dict)
print(liab_heads_dict)
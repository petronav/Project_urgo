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
#img_name = "t2.jpg"
img_name = "bs_new.png"

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
bal_sht_date = "null"
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

	# Check prepared date
	if "Date" in i:
		date_pos_find = i.find("Date")
		prepared_date = i[date_pos_find +5 : date_pos_find +18]

	# Check prepared place
	if "Place" in i:
		plc_pos_find = i.find("Place")
		prepared_place = i[plc_pos_find + 6:]
	# We would check the prepared_date, prepared_place, prepared_by at the bottom part


# Declare lists - one for liability items, one for asset items, one for rupees amounts, one for whole line
liability_items = [] 
asset_items = []
floating_numerics = []
whole_line_list = []


# Declare the asset and liabilities keywords for checking and safe appending in lists
liability_keywords = ["Opening B", "OPENING B", "Drawings", "Income", "Secured L", "Loan", "LOAN", \
			"Current L", "CURRENT L", "Payable", "Sundry Creditors", "Bank OD", "BANK OD", \
			"Advance Received", "Unsecured L", "UNSECURED L", "VAT", "Audit Fee"]

asset_keywords = ["Dep", "Stock in Trade", "Advance", "Sundry Debtors", "Current A", "Bank Bal","BANK B", \
			"Cash & Bank Balance", "Fixed A", "FIXED A", "Investment" , "INVESTMENT", "Cash in Hand",\
		  	"TDS", "A/c no", "Invertor", "Car", "Tool", "Computer", "Furniture", "Mobile", \
		  	"Motor", "Battery"]

# Declare two lists with liability and asset headings
liability_heads = ["Opening B", "OPENING B", "Secured Loan", "SECURED LOAN","Current L", "CURRENT L"]
asset_heads = ["Fixed A", "FIXED A", "Investment", "INVESTMENT", "Current A","CURRENT A", "Bank A", \
	       "BANK A", "Cash & B", "CASH & B", "Loan "]

# Define a function which would return True, position index if there is any liability keyword in a string and False, None otherwise
def check_liab_kword_pres(samp_str):
	tmp_ret = None
	find_pos = 0
	count = 0
	while count < len(liability_keywords):
		if liability_keywords[count] in samp_str:
			tmp_ret = True
			find_pos = samp_str.find(liability_keywords[count])
			break
		else:
			tmp_ret = False
		count += 1
	return tmp_ret, find_pos


# Define another function to check whether any asset keyword is present in a string or not - return True, position index if yes ; False, None otherwise
def check_ast_kword_pres(samp_str):
	tmp_ret_a = None
	count_a = 0
	find_pos = 0
	while count_a < len(asset_keywords):
		if asset_keywords[count_a] in samp_str:
			tmp_ret_a = True
			find_pos = samp_str.find(asset_keywords[count_a])
			break
		else:
			tmp_ret_a = False
		count_a +=1
	return tmp_ret_a, find_pos


# Define a function to check whether any liability heading is present in a string or not - return True, position index if yes ; False, None otherwise
def check_liab_head_pres(samp_str):
	tmp_ret = None
	find_pos = 0
	for i in liability_heads:
		if i in samp_str:
			tmp_ret = True
			find_pos = samp_str.find(i)
			break
		else:
			tmp_ret = False
	return tmp_ret, find_pos


# Define another function to check whether there is any asset heading in a string or not - return True, position index if yes ; False, None otherwise 
def check_ast_head_pres(samp_str):
	tmp_ret_a = None
	find_pos = None
	for i in asset_heads:
		if i in samp_str:
			tmp_ret_a = True
			find_pos = samp_str.find(i)
			break
		else:
			tmp_ret_a = False
	return tmp_ret_a, find_pos
print(check_ast_kword_pres("CAPITAL & LIABILITIES ‘AMOUNT ASSETS & PROPERTY AMOUNT")[0])
print(type(check_ast_kword_pres("CAPITAL & LIABILITIES ‘AMOUNT ASSETS & PROPERTY AMOUNT")[0]))

table_head_line_no = 0
# Check from which line the table starts
for i in content:
	print(i)
	if "AMOUNT" in i or "Amount" in i:
		table_head_line_no = content.index(i)
print(table_head_line_no)

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



# Go through all the table lines starting from the position of table headline 
for i in content[table_head_line_no+1:]:
	i = i.replace("  ",",")
	print("line : ",i)
	# Get all the floating numeric values in a list from a line
	floating_numerics = re.findall(r'((?:\d+,*)+\d+\.\d{2})', i)
	print("numbers list : ",floating_numerics)

	# If a line contains only strings and no floating numerics then they should be either liability head or asset head
	# However sometimes there may be some liability or asset items which aren't heads but aren't attached with any floating numeric 
	if len(floating_numerics) == 0 :
		i = i.strip()
		# Check if they contain any liability headings
		if i == "":
			pass
		elif check_ast_head_pres(i)[0] == True :
			if check_liab_head_pres(i)[0] == True:
				a_h_pos = check_liab_head_pres(i)[1]
				asset_items.append([i[a_h_pos:]])
			else:
				asset_items.append([i])
		elif check_ast_head_pres(i)[0] == False :
			if check_liab_head_pres(i)[0] == True:
				liability_items.append([i])
		else:
			continue

						
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
		
		# There are six possibilities :
		# poss 1 : liability_string    liability_value    asset_string
		# poss 2 : liability_string    liability_value
		# poss 3 : 					  asset_string    asset_value
		# poss 4 : liability_string			  asset_string    asset_value
		# poss 5 : 		       liability_value    asset_string
		# poss 6 : 		       liability_value

		# Matching cases :
		# case 1 : string_before_val       numeric_val    string_after_val   	 >> poss 1
		# case 2 : string_before_val       numeric_val    NO_string_after_val 	 >> poss 2, 3, 4
		# case 3 : NO_string_before_val    numeric_val    string_after_val       >> poss 5
		# case 4 : NO_string_before_val    numeric_val    NO_string_after_val	 >> poss 6

		# case 1:
		if len(re.findall(r'\w',string_aftr_floating_numerics)) != 0 and len(re.findall(r'\w',string_bfr_floating_numerics)) !=0:
			liability_items.append([string_bfr_floating_numerics, floating_numerics[0]])
			asset_items.append([string_aftr_floating_numerics])

		# case 2:
		elif len(re.findall(r'\w',string_aftr_floating_numerics)) == 0 and len(re.findall(r'\w',string_bfr_floating_numerics)) !=0:
			# poss 2
			if check_liab_kword_pres(string_bfr_floating_numerics)[0] == True and check_ast_kword_pres(string_bfr_floating_numerics)[0] == False:
				liability_items.append([string_bfr_floating_numerics, floating_numerics[0]])
			# poss 3
			elif check_ast_kword_pres(string_bfr_floating_numerics)[0] == True and check_liab_kword_pres(string_bfr_floating_numerics)[0] == False:
				asset_items.append([string_bfr_floating_numerics, floating_numerics[0]])
			# poss 4
			elif check_liab_kword_pres(string_bfr_floating_numerics)[0] == True and check_ast_kword_pres(string_bfr_floating_numerics)[0] == True:
				ast_kw_pos = check_ast_kword_pres(string_bfr_floating_numerics)[1]
				liability_items.append([string_bfr_floating_numerics[:ast_kw_pos]])
				asset_items.append([string_bfr_floating_numerics[ast_kw_pos:],floating_numerics[0]])

		# case 3 and 4:
		elif len(re.findall(r'\w',string_bfr_floating_numerics)) == 0 :
			liability_items.append([floating_numerics[0]])
			# poss 5
			if len(re.findall(r'\w',string_aftr_floating_numerics)) !=0:
				asset_items.append([string_aftr_floating_numerics])
			else:
				pass
		"""
		# There are three situations for having only one numeric in a line :
		# 1>	liability item ... liability amount ... asset item
		# 2>	liability item ... liability amount ... ' '
		# 3>	"THERE MAY BE SOME liability item"  ... asset item ... asset amount

		# If the chunk of strings after the numeric is not vacant : it is the first case
		if len(re.findall(r'\w',string_aftr_floating_numerics)) != 0:
			liability_items.append([string_bfr_floating_numerics, floating_numerics[0]])
			asset_items.append([string_aftr_floating_numerics])

		# If the chunk of strings after the numeric is vacant : this invokes the last two cases 
		elif len(re.findall(r'\w',string_aftr_floating_numerics)) == 0:
			# For the last case, we need to check both for liability and asset keywords
			print(string_bfr_floating_numerics)
			if check_liab_kword_pres(string_bfr_floating_numerics)[0] == True :
				if check_ast_kword_pres(string_bfr_floating_numerics)[0] == True :
					ast_kw_pos = check_liab_kword_pres(string_bfr_floating_numerics)[1]
					liability_items.append([string_bfr_floating_numerics[:ast_kw_pos]])
					asset_items.append([string_bfr_floating_numerics[ast_kw_pos:], floating_numerics[0]])
				else:
					liability_items.append([string_bfr_floating_numerics,floating_numerics[0]])
			elif check_liab_kword_pres(string_bfr_floating_numerics)[0] == False :
				if check_ast_kword_pres(string_bfr_floating_numerics)[0] == True :
					asset_items.append([string_bfr_floating_numerics, floating_numerics[0]])
		
		"""
		# Append the chunk of strings and numeric in whole line list 
		whole_line_list.append([string_bfr_floating_numerics, floating_numerics[0],string_aftr_floating_numerics])
	
	elif len(floating_numerics) == 2:
		# Four possibilities :
		# poss 1 : liability_string    liability_value    liability_value    asset_string
		# poss 2 : liability_string    liability_value    liability_value    
		# poss 3 : liability_string    liability_value                       asset_string    asset_value
		# poss 4 :                     liability_value                       asset_string    asset_value
		# poss 5 : 							     asset_string    asset_value    asset_value

		# Matching cases :
		# case 1 : first_string    first_val    NO_middle_string    second_val    last_string 				>> poss 1 
		# case 2 : first_string    first_val    NO_middle_string    second_val    NO_last_string			>> poss 2 and 5
		# case 3 : first_string    first_val    middle_string       second_val    NO_last_string			>> poss 3
		# case 4 : NO_first_string first_val    middle_string       second_val    NO_last_string			>> poss 4


		# Get the lengths and starting positions of the two numeric items 
		first_floating_item_pos = i.find(floating_numerics[0])
		first_floating_item_len = len(floating_numerics[0])
		second_floating_item_pos = i.find(floating_numerics[1])
		second_floating_item_len = len(floating_numerics[1])

		# Get three chunks of strings in between the two floating items
		first_string = i[:first_floating_item_pos]
		middle_string = i[first_floating_item_pos + first_floating_item_len:second_floating_item_pos]
		last_string = i[second_floating_item_pos + second_floating_item_len:]

		# Case 1
		if len(re.findall(r'\w',middle_string)) == 0 and len(re.findall(r'\w',last_string)) !=0:
			liability_items.append([first_string,floating_numerics[0]])
			asset_items.append([last_string])
		# case 2
		elif len(re.findall(r'\w',middle_string)) == 0 and len(re.findall(r'\w',last_string)) == 0 :
			# possibility 2
			if check_liab_kword_pres(first_string)[0] == True:
				liability_items.append([first_string,floating_numerics[0]])
			# possibility 5
			else:
				asset_items.append([first_string,floating_numerics[0]])
		# case 3
		elif len(re.findall(r'\w',middle_string)) != 0:
			if len(re.findall(r'\w',last_string)) == 0:
				asset_items.append([middle_string, floating_numerics[1]])
				liability_items.append([first_string, floating_numerics[0]])
			else:
				pass


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
			print("line405")
			print([first_string, floating_numerics[0], floating_numerics[1] ])
			liability_items.append([first_string, floating_numerics[0], floating_numerics[1] ])
			asset_items.append([last_string , floating_numerics[2] ])

			whole_line_list.append([first_string,floating_numerics[0],floating_numerics[1],last_string,floating_numerics[2]])

		# If end string contains no words :
		# The initial string must be liability item 
		# The middle string must be asset item
		# In this case, the initial numeric is liability value, middle numeric is asset value, end numeric is total asset value
		# Visual Format :
		# liability item ... liability value ... asset item ... asset value ... total asset value ... ' ' 
		elif len(re.findall(r'\w',last_string)) == 0 and len(re.findall(r'\w',middle_string)) != 0:
			asset_items.append([middle_string, floating_numerics[1], floating_numerics[2] ])
			if len(re.findall(r'\w',first_string)) != 0 : 
				liability_items.append([first_string, floating_numerics[0] ])
			else:
				liability_items.append([floating_numerics[0]])

			whole_line_list.append([first_string,floating_numerics[0],middle_string,floating_numerics[1],floating_numerics[2]])


# Delete duplicate items in the list of asset items and liability items
asset_items = [ii for n,ii in enumerate(asset_items) if ii not in asset_items[:n]]
liability_items = [ii for n,ii in enumerate(liability_items) if ii not in liability_items[:n]]


# Cleanse all \n -s from the strings in the list of asset items and liability items
for i in asset_items:
	for j in i:
		j = j.replace("\n","")


for i in liability_items:
	for j in i:
		j = j.replace("\n","")



# Check the main asset heading positions 
fixed_asset_index = 0
current_asset_index =0
investment_index = 0
cash_bank_bal_acc_index = 0
for i in asset_items:
	for j in i:
		# Check for asset headings
		if "Fixed A" or "FIXED A" in j:
			fixed_asset_index = asset_items.index(i)
		if "Current A" or "CURRENT A" in j:
			current_asset_index = asset_items.index(i)
		if "Investment" or "INVESTMENT" in j:
			investment_index= asset_items.index(i)
		if "Bank B" or "BANK B" or "Cash" or "CASH" or "Bank Ac" or "BANK AC"in j:
			cash_bank_bal_acc_index = asset_items.index(i)
# Create a dictionary with keys as asset headings and their position as values
ast_heads_dict = {"fixed_asset" : fixed_asset_index, "current_asset" : current_asset_index,\
					"investment" : investment_index, "cash_bank_bal_acc" : cash_bank_bal_acc_index}

# Check the main liability heading positions 
capital_index = 0
loan_index = 0
current_liabilities_index = 0
for m in liability_items:
	for n in m:
		# Check for liability headings
		if "Capital" or "CAPITAL" in n:
			capital_index = liability_items.index(m)
		if "Secured L" or "SECURED L" or " Loan" or " LOAN" in n:
			loan_index = liability_items.index(m)
		if "Current L" or "CURRENT L" in n:
			current_liabilities_index = liability_items.index(m)
# Create a dictionary with keys as liability headings and their position as values
liab_heads_dict = {"capital" : capital_index, "secured_loan" : loan_index, "current_liabilities" : current_liabilities_index}

print(liability_items)
print(asset_items)
print(whole_line_list)


print(ast_heads_dict)
print(liab_heads_dict)

ast_json_list = []
liab_json_list = []
"""
# For adding liability types  
for i in liability_items:
	print("line454",i)
	temp_indx = liability_items.index(i)
	next_itm = liability_items[temp_indx+1]
	next_next_itm = liability_items[temp_indx+2]
	if "Add" in next_itm[0]:
		additions = {next_itm[0] : next_itm[1] if len(next_itm)==2 else next_itm[0]
					}
	if "Less" or "Drawings" in next_next_itm[0]:
		reductions = {next_next_itm[0] : next_next_itm[1] if len(next_next_itm) ==2 else next_next_itm[0]
						}
	liab_json_list.append({"liability name" : i[0],\
								"liability value" : i[1] if len(i)==2 else i[0],\
								"additions" : additions,\
								"reductions" : reductions\

			})

"""

for i in liability_items:
	liab_json_list.append({"liability name" : i[0], "liability value" : i[1] if len(i)!=1 else ""})

for i in asset_items:
	ast_json_list.append({"asset name" : i[0], "asset value" : i[1] if len(i)!=1 else ""})



out_json_final = {
	"business name" : business_name,
	"business owner" : business_owner,
	"Address" : address,
	"Date of Birth" : date_of_birth,
	"PAN Number" : pan_no,
	"balance sheet date" : bal_sht_date,
	"prepared date" : prepared_date,
	"prepared place" : prepared_place,
	"prepared by" : prepared_by,
	"Assets" : ast_json_list,
	"Liabilities" : liab_json_list
}

print(" * * * *  * * *  * *  * *  * * * * * * * *")
print(json.dumps(out_json_final, indent = 4))

json_fname = img_name[:img_name.find(img_name.split('.')[-1]) - 1] + ".json"

with open(json_fname, "w") as fp:
    json.dump(out_json_final , fp, indent =4) 

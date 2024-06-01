from importlib import import_module
from django.contrib.contenttypes.models import *
from django.core.cache import cache
from django.core.exceptions import *
from django.db.models import QuerySet
import random
import string
import copy
from uuid import UUID
from django.forms.models import model_to_dict
from django.db.models import Case, When
import re
from content.contants import *
from math import ceil
import json

from django.db.transaction import atomic

@atomic()
def bulk_saves(list):
    for item in list:
        item.save()

from datetime import datetime, timedelta

class DataPathError(Exception):
	pass

class LayoutDefineError(Exception):
	pass

CONTENTFIELDS=None
FIELDS=None
CONTENTS=None
ACTIONS=None
SITEDATA=None
DATATYPES=None

PUBLISHLIST= ["Public","Guest","Task Owner","Staff","Private"]



def week_of_month(dt):
	""" Returns the week of the month for the specified date.
	"""

	first_day = dt.replace(day=1)
	dom = dt.day
	adjusted_dom = dom + first_day.weekday()

	return int(ceil(adjusted_dom/7.0))

class PageNotFound(Exception):
	pass

class PathNotFound(Exception):
	pass

class MethodNotFound(Exception):
	pass

def get_website_data():
	from content.models import ContentData
	key_name = "website"
	global SITEDATA
	if not SITEDATA:
		SITEDATA = cache.get(key_name)
	if not SITEDATA:
		SITEDATA = ContentData.objects.get(content__name="website")
		SITEDATA.target = SITEDATA.get_obj()
		cache.set(key_name, SITEDATA)
	return copy.deepcopy(SITEDATA)

def get_role_type(id):
	from content.models import DataType
	global DATATYPES
	if not DATATYPES:
		DATATYPES = set_datatype_objects()
	if (str(id) in DATATYPES):
		return DATATYPES[str(id)]

def get_dyn_roles():
	from content.models import Role
	key_name = "dyn_roles"
	res = cache.get(key_name)
	if not res:
		res = [role for role in Role.objects.filter(static=False).order_by("permission")]
		cache.set(key_name, res)
	return res

def get_site_roles():
	from content.models import Role
	key_name = "site_roles"
	res = cache.get(key_name)
	if not res:
		res = [role for role in Role.objects.filter(static=True, team=None).order_by("permission")]
		cache.set(key_name, res)
	return res


def getter_objects_get(id=None):
	from content.models import ContentGetter
	key_name = "getter"
	res = cache.get(key_name)
	if not id:
		return None
	if not res:
		res = {}
		getters = ContentGetter.objects.all()
		for getter in getters:
			res[str(getter.id)] = getter
		cache.set(key_name,res)
	return res[str(id)]

def action_objects_all():
	key_name = "action"
	global ACTIONS
	if not ACTIONS:
		ACTIONS = cache.get(key_name)
	if not ACTIONS:
		ACTIONS = set_action_objects()
	return [ACTIONS[key] for key in ACTIONS]

def set_action_objects():
	from content.models import Action
	key_name = "action"
	res = {}
	actions = Action.objects.all()
	for action in actions:
		res[str(action.id)] = action
	cache.set(key_name,res)
	return res

def set_datatype_objects():
	from content.models import DataType
	key_name = "datatype"
	res = {}
	datatypes = DataType.objects.all()
	for datatype in datatypes:
		res[str(datatype.id)] = datatype
	cache.set(key_name,res)
	return res


def action_objects_get(id=None):
	key_name = "action"
	global ACTIONS
	ACTIONS = cache.get(key_name)
	if not id:
		return None
	if not ACTIONS:
		ACTIONS = set_action_objects()
	return copy.deepcopy(ACTIONS[str(id)])

def action_create_get(content):
	key_name = "action"
	global ACTIONS
	ACTIONS = cache.get(key_name)
	if not ACTIONS:
		ACTIONS = set_action_objects()
	for key in ACTIONS:
		if ACTIONS[key].content_id == content.id and ACTIONS[key].is_initializer:
			return ACTIONS[key]

def action_content_get(content,name):
	key_name = "action"
	global ACTIONS
	ACTIONS = cache.get(key_name)
	if not ACTIONS:
		ACTIONS = set_action_objects()
	for key in ACTIONS:
		if ACTIONS[key].content_id == content.id and ACTIONS[key].name == name:
			return ACTIONS[key]

def page_objects_get(id=None):
	from content.models import Page
	key_name = "page"
	res = cache.get(key_name)
	if not id:
		return None
	if not res:
		res = {}
		pages = Page.objects.all()
		for page in pages:
			res[str(page.id)] = page
		cache.set(key_name,res)
	return res[str(id)]

def page_content_get(content,is_list=True):
	from content.models import Page
	key_name = "page"
	res = cache.get(key_name)
	if not res:
		res = {}
		pages = Page.objects.all()
		for page in pages:
			res[str(page.id)] = page
		cache.set(key_name,res)

	for key in res:
		page = res[key]
		if page.content == content and page.is_list == is_list:
			return key



def template_objects_get(id=None):
	from content.models import Template
	key_name = "template"
	res = cache.get(key_name)
	if not id:
		return None
	if not res:
		res = {}
		templates = Template.objects.all()
		for template in templates:
			res[str(template.id)] = template
		cache.set(key_name,res)
	return res[str(id)]

def set_content_objects():
	key_name="content"
	res = {}
	from content.models import Content
	contents = Content.objects.all()
	for content in contents:
		res[str(content.id)] = content
		res[content.name] = content
	cache.set(key_name, res)
	return res

def set_toggle_func(funcs):
	if "toggleExpanded" not in funcs:
		funcs["toggleExpanded"] = """function(item,name){							
								item.expanded=!item.expanded; 
								if(!this.expanded){this.expanded = {}};										
								name_item=name.split(".")[0].split("[")[0];
								if (!this.expanded[name_item]){
									this.expanded[name_item] = {}
								}
								this.expanded[name_item][name] = item.expanded;
								var expanded = false;
								for (var key in this.expanded[name_item]){
									expanded = expanded || this.expanded[name_item][key] 
								}
								if (expanded && this.heights && this.heights[name_item+"_raw"]){this.heights[name_item]=this.heights[name_item+"_raw"]}
								else{if (this.heights){this.heights[name_item]='auto'}}}"""
	return funcs


def content_objects_get(id=None,name=None):
	from content.models import Content
	global CONTENTS
	key_name="content"
	if not CONTENTS:
		CONTENTS = cache.get(key_name)
	if not id and not name:
		return None
	if not CONTENTS:
		CONTENTS = set_content_objects()
	if id and str(id) in CONTENTS:
		return copy.deepcopy(CONTENTS[str(id)])
	if name and name in CONTENTS:
		return copy.deepcopy(CONTENTS[name])
	if id:
		content = Content.objects.get(id=id)
	if name:
		content = Content.objects.get(name=name)

	CONTENTS[content.id] = content
	CONTENTS[content.name] = content
	cache.set(key_name, CONTENTS)
	return content

def set_field_objects():
	key_name="field"
	from content.models import Field
	res = {}
	fields = Field.objects.all()
	for field in fields:
		res[str(field.id)] = field
	cache.set(key_name, res)
	return res


def field_objects_get(id=None):
	from content.models import Field
	global FIELDS
	key_name="field"
	if not FIELDS:
		FIELDS = cache.get(key_name)
	if not id:
		return None
	if not FIELDS:
		FIELDS = set_field_objects()
	if id and str(id) in FIELDS:
		return copy.deepcopy(FIELDS[str(id)])
	if id:
		field = Field.objects.get(id=id)

	FIELDS[str(field.id)] = field
	cache.set(key_name, FIELDS)
	return copy.deepcopy(field)

def contentfield_objects_all(content_name=None):
	key_name = "contentfield"
	global CONTENTFIELDS
	if not CONTENTFIELDS:
		CONTENTFIELDS = cache.get(key_name)
	if not CONTENTFIELDS:
		CONTENTFIELDS = set_content_fields()
	field_dicts = {}
	for field in CONTENTFIELDS:
		for key in CONTENTFIELDS[field]:
			if key not in field_dicts:
				field_dicts[key] = []
			field_dicts[key].append(CONTENTFIELDS[field][key])
	if content_name in field_dicts:
		return field_dicts[content_name]
	return []

def content_field_filter(content_name,columns):
	return filter(lambda x:x.name  in columns, contentfield_objects_all(content_name))

def set_content_fields():
	from content.models import ContentField
	key_name = "contentfield"
	res = {"$id":{}}
	contentFields = ContentField.objects.all()
	for contentField in contentFields:
		content = content_objects_get(id=contentField.content_id)
		if contentField.name not in res:
			res[contentField.name]={}
		if content:
			res[contentField.name][content.name] = contentField
		else:
			res[contentField.name]["none"] = contentField
		res["$id"][str(contentField.id)] = contentField
	cache.set(key_name,res)
	return res


def contentfield_objects_get(name=None, content_name=None,id=None):
	from content.models import ContentField
	key_name = "contentfield"
	global CONTENTFIELDS
	if not CONTENTFIELDS:
		CONTENTFIELDS = cache.get(key_name)
	if not CONTENTFIELDS:
		CONTENTFIELDS = set_content_fields()
	field = None
	if id:
		if int(id) in CONTENTFIELDS["$id"]:
			return copy.deepcopy(CONTENTFIELDS["$id"][int(id)])
		if str(id) in CONTENTFIELDS["$id"]:
			return copy.deepcopy(CONTENTFIELDS["$id"][str(id)])
		else:
			CONTENTFIELDS = set_content_fields()
			return copy.deepcopy(CONTENTFIELDS["$id"][str(id)])
	if name and name.find(FIELD_SEPARATOR) > 0:
		field_name, content_name, index = name.split(FIELD_SEPARATOR)
	else:
		field_name = name


	if not content_name or content_name.lower() == "none":
		content_name = "none"
	if field_name in CONTENTFIELDS and content_name in CONTENTFIELDS[field_name]:
		contentField = CONTENTFIELDS[field_name][content_name]
		field = copy.deepcopy(contentField)

	elif not field_name in CONTENTFIELDS:
		CONTENTFIELDS[field_name] = {}
		try:
			if content_name == "none":
				CONTENTFIELDS[name][content_name] = ContentField.objects.get(name=field_name, content=None)
			else:
				CONTENTFIELDS[name][content_name] = ContentField.objects.get(name=field_name, content__name = content_name)

		except Exception as e:
			print "name : " + field_name
			print "content_name :" + content_name
			if content_name and not content_name == "none":
				field = contentfield_objects_get(field_name)
			else:
				raise e
		cache.set(key_name, CONTENTFIELDS)
	elif field_name in CONTENTFIELDS and "none" in CONTENTFIELDS[field_name]:
		field =  copy.deepcopy(CONTENTFIELDS[field_name]["none"])
	if content_name in CONTENTFIELDS[field_name]:
		field =  copy.deepcopy(CONTENTFIELDS[field_name][content_name])
	else:
		print "name : " + field_name
		print "content_name :" + content_name

	if field:
		field.name = name
		return field


def dict_replace(item, src, target):
	if type(item) == str or type(item) == unicode:
		return item.replace(src,target)
	if type(item) == list:
		res = []
		for i_item in item:
			res.append(dict_replace(i_item,src,target))
		return res
	if type(item) == dict:
		res={}
		for key in item:
			name = key.replace(src,target)
			res[name] = dict_replace(item[key],src,target)
		return res
	return item


def get_func(func_name):
	module, func = func_name.rsplit('.', 1)
	mod = import_module(module)
	print func
	if hasattr(mod, func):
		return getattr(mod, func)
	else:
		raise MethodNotFound

def getDict(obj):
#	return {'id':obj.id}
	if isinstance(obj,models.Model):
		res = model_to_dict(obj)
		for key in res:
			if isinstance(res[key],QuerySet):
				res[key]=[item.id for item in res[key].all()]
			if isinstance(res[key],datetime):
				res[key]=str(res[key])
			if isinstance(res[key],UUID):
				res[key] = str(res[key])
			if isinstance(res[key],list):
				item_list = []
				for obj_item in res[key]:
					if isinstance(obj_item,models.Model):
						item_list.append(obj_item.id)
					else:
						item_list.append(obj_item)
				res[key] = item_list
			if not res[key]:
				res[key] = None
		return res
	return obj

def setupContentObj(obj, language=None):
	res = {}
	if hasattr(obj,"data"):
		for key in obj.data:
			if not key.startswith("$") and key not in ["langs"]:
				res[key] = obj.data[key]
		if "langs" in obj.data and language:
			for lang_item in obj.dat["langs"]:
				if language.upper() == lang_item["lang_select"].upper():
					for key in lang_item:
						res[key] = lang_item[key]
	return res

	return res

def get_or_create(clazz,**dict):
	obj, created = clazz.objects.get_or_create(**dict)
	if (created):
		obj.save()
	return obj

def generate_key(length):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def generateObj(jsonData,data):
	if "$obj" in jsonData:
		return jsonData["$obj"]
	if "$model" in jsonData:
		print jsonData
		content = ContentType.objects.get(model=jsonData["$model"].lower())
		clazz = content.model_class()

		if "$get_or_create" in jsonData:
			getContent = parseObj(jsonData["$get_or_create"],data)
			obj,created = clazz.objects.get_or_create(**getContent)
			if created:
				obj.save()
		else:
			params = parseObj(jsonData["$params"], data)
			if not "id" in params or not params["id"]:
				if hasattr(clazz,"createObj"):
					obj = clazz.createObj(**params)
				else:
					obj = clazz(**params)
				print clazz
				print jsonData["$params"]
				print params
				obj.save()
				jsonData["id"] = obj.id
			else:
				obj = clazz.objects.get(id = params["id"])
		return obj
	if "$class" in jsonData:
		print jsonData["$class"]
		module, clazz = jsonData["$class"].rsplit('.',1)
		mod = import_module(module)
		if hasattr(mod,clazz):
			clazz = getattr(mod,clazz)
			params = parseObj(jsonData["$param"], data)
			return clazz(**params)
	if "$method" in jsonData:
		if "$self" in jsonData:
			obj = parseObj(jsonData["$self"],data)
			func = getattr(obj,jsonData["$method"])
		else:
			func = get_func(jsonData["$method"])
		if "$params" in jsonData:
			params = parseObj(jsonData["$params"], data)
			if  isinstance(params,dict):
				return func(**params)
			elif isinstance(params,list):
				return func(*params)
			else:
				return func(params)
		else:
			return func()
	return jsonData

def processData(data):
	params = {}
	for key in data:
		field = key.split(FIELD_SEPARATOR)[0]
		params[field] = data[key]
	return params


def getObj(name,data):
	if name in data:
		return generateObj(data[name],data)


def jsonize(data):
	if "$obj" in data:
		obj = data.pop("$obj")
		if hasattr(obj, "id"):
			if "$params" not in data:
				data["$params"] = {}
			data["$params"]["id"] = obj.id
		return obj
		# obj_id = obj.__class__.__name__ + "_" + str(obj.id)
		# data["$objs"][obj_id] = data[key]
		# data["$objs"][obj_id]["$name"] = key


def getRefObj(ref_str,data):
	items = ref_str.split(".")
	ref = items[0]
	if not data:
		return None

	if ref == "$root":
		return data

	if ref not in data:
		return None
	if isinstance(data[ref], dict):
		obj = generateObj(data[ref], data)
		if obj:
			if "$obj" not in data[ref] and isinstance(obj,models.Model) :
				data[ref]["$obj"] = obj
		else:
			obj = parseObj(data[ref], data)
	else:
		obj = parseObj(data[ref], data)
	if len(items) > 1:
		for item in items[1:]:
			try:
				try:
					obj = getattr(obj, item)
				except AttributeError:
					obj = obj.__getitem__(item)
			except :
				obj = None
	return obj

def getDataList(user,team,datalist):
	res = []
	for contentData in datalist:
		if team:
			if contentData.security == 1 or (contentData.security <= 2 and user.is_authenticated()) or (user.is_authenticated() and \
						((contentData.security <= 3 and team and team.is_member(user)) or \
						(contentData.security <= 4 and team and team.is_manager(user)) or \
						contentData.is_owner(user) or user.is_staff)):
				res.append(contentData)
		else:
			if contentData.security == 1 or (contentData.security <= 2 and user.is_authenticated()):
				res.append(contentData)
	return res

def getLangName(lang_code):
	if lang_code == "zh-CN":
		return "Simplified Chinese"
	if lang_code == "zh-TW":
		return "Traditional Chinese"
	if lang_code.startswith("en"):
		return "English"

def getLangData(data,language,field_name):
	if "langs" in data:
		for lang_item in data["langs"]:
			if lang_item["lang_select"] == language and field_name in lang_item:
				return lang_item[field_name]

def getLangFields(fieldData,data,language):
	for field_name in fieldData:
		if field_name.startswith("select_field"):
			for field_item in fieldData[field_name]:
				if "field" in field_item and "title" in field_item:
					field_item["title"],field_item_name = getFieldTitleFromData(field_item["field"],None,data,language)
	return fieldData

def setLangData(obj, data):
	if "langs" in data:
		if obj.data:
			obj.data["langs"] = data["langs"]
		else:
			obj.data = {"langs": data["langs"]}


def setFuncs(funcs, template_funcs):
	for func in template_funcs:
		if not func == "init":
			funcs[func] = template_funcs[func]
		else:
			funcs["init"].extend(template_funcs["init"])
	return funcs


#$ref : jsonpath, $type: datatype
def parseObj(param,data, dataList=None):
	#print param
	if isinstance(param, dict):
		if "$ref" in param:
			if dataList:
				return dataList[param["$ref"]]
			else:
				ref_str = param["$ref"]
				return getRefObj(ref_str,data)
		elif "$method" in param or "$class" in param or "$model" in param:
			return generateObj(param,data)
		elif "$fields" in param:
			obj = getRefObj(param["$fields"],data)
			params = {}
			for field in obj:
				params[field] = data[field]
			return params
		else:
			params = {}
			for key in param:
				params[key] = parseObj(param[key], data)
			return params
	elif isinstance(param, list):
		params = []
		for item in param:
			params.append(parseObj(item,data))
		return params
	return param


def merge(a, b, path=None,obj=None):
	"merges b into a"
	if path is None: path = []
	for key in b:
		if key in a:
			if isinstance(a[key], dict) and isinstance(b[key], dict):
				merge(a[key], b[key], path + [str(key)])
			else:
				a[key] = b[key]
		else:
			a[key] = b[key]
	return a

def getLayout(layout,field_name,name):
	field_paths = field_name.split("[]")
	i = 0
	field_array = ""
	field_prefix = ""
	length = len(field_paths)
	for field_path in field_paths[:length - 1]:
		field_array += field_path + "[arrayIndices[" + str(i) + "]]"
		#				field_prefix += "model."+field_array + "||"
		i = i + 1
	field_prefix += field_array + field_paths[length - 1]
	field_array = field_prefix + "[arrayIndices[" + str(i) + "]]"
	items = field_prefix.split(".")
	field_condition = ""
	for j in range(1, len(items) + 1):
		k = items[j - 1].find("[")
		if k > 0:
			if j > 1:
				field_condition += "!model." + ".".join(items[:j - 1]) + "." + items[j - 1][:k] + "||"
			else:
				field_condition += "!model." + items[j - 1][:k] + "||"
		field_condition += "!model." + ".".join(items[:j]) + "||"

	layout = layout.replace("$field[arrayIndices]", field_array)
	layout = layout.replace("!model.$field||", field_condition)
	layout = layout.replace("model.$field", "model." + field_prefix)
	layout = layout.replace("$index",str(i))
	layout = layout.replace("$field", field_name).replace("$no_prefix", name)
	return layout

def getFieldId(fieldsData,fieldTitle):
	langTitles = fieldsData["English"]
	for key in langTitles:
		if key.lower() == fieldTitle.lower():
			return langTitles[key]

#change language to be English
def reconcileLangField(data,fieldsData,language, method):
	if type(data)==dict:
		for key in data:
			if key.startswith("lang_select"):
				fieldData = getFieldDataFromCfg(key,fieldsData)
				langFieldId = fieldData["enum"]
				lang_dict = {}
				for lang_item in fieldData["langs"]:
					lang_dict[lang_item["lang_select"]] = lang_item
				value = lang_dict[language][langFieldId]
				if method == "set":
					data[key] = LANG_LIST[value.index(data[key])]
				else:
					data[key] = value[LANG_LIST.index(data[key])]
			else:
				data[key] = reconcileLangField(data[key], fieldsData, language, method)
		return data
	elif type(data) == list:
		res = []
		for item in data:
			res.append(reconcileLangField(item,fieldsData,language,method))
		return res
	else:
		return data

def getFieldCount(name, content_name, contentData):
	parents = contentData.parents
	parents.reverse()
	parents.append(contentData)


	fields_data = {}
	for parent in parents:
		if "$fields" in parent.data:
			merge(fields_data, parent.data["$fields"])

	if name not in fields_data:
		return 0

	if content_name not in fields_data[name]:
		return 0
	index_list = fields_data[name][content_name].keys()
	if "default" in index_list:
		index_list.remove("default")

	return max([int(index) for index in index_list]) + 1


def paramFieldData(data,content,fieldsData,field_name,language):
	# fieldData = getFieldDataFromCfg("lang_select", fieldsData)
	# fieldData = copy.deepcopy(getProjectData(fieldData, language))
	from content.models import ContentField

	if field_name.find(FIELD_SEPARATOR) > 0:
		fieldItems = field_name.split(FIELD_SEPARATOR)
		if fieldItems[0] not in fieldsData:
			fieldsData[fieldItems[0]] = {}
		if "default" in fieldsData[fieldItems[0]]:
			fieldsData[fieldItems[0]].pop("default")
		if fieldItems[1] not in fieldsData[fieldItems[0]]:
			fieldsData[fieldItems[0]][fieldItems[1]] = {}
		fieldContentData = fieldsData[fieldItems[0]][fieldItems[1]]
		if not fieldItems[1] == "none":
			contentField = ContentField.objects.get(name=fieldItems[0], content__name=fieldItems[1])
		else:
			contentField = ContentField.objects.get(name=fieldItems[0], content = None)

		cfgDict = {}
		values={}
		for cfgItem in contentField.data["configure"]:
			paths = cfgItem["path"].split(",")
			for path in paths:
				if path.startswith("configure"):
					configure = ".".join(path.split(".")[1:])
					cfgDict[configure] = cfgItem['field']
					if not cfgItem['field']:
						cfgDict[configure] = getFieldId(fieldsData,cfgItem['name'])

		merge(data,cfgDict)
		if not data[NEW_FIELD]:
			index = fieldItems[2]
		else:
			index = getFieldCount(fieldItems[0],fieldItems[1],content)
		fieldContentData[str(index)] = data
		if data[DEFAULT_FIELD]:
			fieldContentData["default"] = str(index)

		index_name = fieldItems[0] + FIELD_SEPARATOR + fieldItems[1] + FIELD_SEPARATOR + str(index)
		lang_list = LANG_LIST
		for lang in data["langs"]:
			lang_name = lang["lang_select"]
			if lang_list.index(lang_name) >= 0 :
				lang_value = LANG_LIST[lang_list.index(lang_name)]
				if lang_value not in fieldsData:
					fieldsData[lang_value] = {}
				field_title = lang[FIELD_TITLE]
				fieldsData[lang_value][field_title] = index_name
	return fieldsData


def projectLangData(data, language):
	if language:
		if type(data) == dict:
			if "langs" in data:
				data = getProjectData(data, language)
			for key in data:
				data[key] = projectLangData(data[key], language)
		if type(data) == list:
			res = []
			for item in data:
				res.append(projectLangData(item,language))
			data = res
	return data


def getProjectData(fieldData,language):
	if "langs" in fieldData:
		lang_dict = {}
		for lang_item in fieldData["langs"]:
			lang_dict[lang_item["lang_select"]] = lang_item
		if language in lang_dict:
			for key in lang_dict[language]:
				fieldData[key] = lang_dict[language][key]
	return fieldData

def reconcileData(data, cfgData, fieldsData, language, method, contentField=None):
	langDict = {}
	from content.models import ContentField
	if contentField and contentField.form_field > 0:

		for field in contentField.form:
			fieldContent = contentField.content
			if fieldContent:
				subField = contentfield_objects_get(name = field,content_name=fieldContent.name)
			else:
				subField = contentfield_objects_get(name=field, content_name="none")

			subData = getFieldDataFromCfg(subField, fieldsData)

			if contentField.form_field == 2:
				for itemData in data:
					if field in itemData:
						itemData[field] = reconcileData(itemData[field],subData,fieldsData,language,method, subField)
			else:
				if data and field in data:
					if type(data) == str:
						data=json.loads(data)
					data[field] = reconcileData(data[field], subData, fieldsData, language, method,subField)


		if contentField.form_field == 2:
			for itemData in data:
				if "langs" in itemData:
					itemData["langs"] = reconcileLangField(itemData["langs"], fieldsData, language, method)
		elif data and "langs" in data:
			data["langs"] = reconcileLangField(data["langs"], fieldsData, language, method)


	elif language:
		data = reconcileLangField(data,fieldsData,language, method)

	if cfgData and "langs" in cfgData:
		for lang_item in cfgData["langs"]:
			langDict[lang_item["lang_select"]] = lang_item
		if language in langDict:
			langData = langDict[language]
		elif "English" in langDict:
			langData = langDict["English"]
		for key in cfgData:
			if key.startswith("enum"):
				field_id = cfgData[key]
				fieldOptions = langData[field_id]
				paths = key.split(".")
				data = getEnumData(data,paths[1:],fieldOptions,method)
		return data
	return data

def getParams(data):
	params = {}
	for key in data.keys():
		params[key.split(FIELD_SEPARATOR)[0]] = data[key]
	return params

def getEnumData(data, paths, fieldOptions,method):
	if len(paths) == 0:
		if method == "get":
			try:
				return fieldOptions[data]
			except:
				return data
		elif method == "set":
			if data in fieldOptions:
				return fieldOptions.index(data)
			else:
				return data
		return data
	if not paths[0] == "items":
		if paths[0] in data:
			data[paths[0]] = getEnumData(data[paths[0]], paths[1:], fieldOptions,method)
		return data
	else:
		res = []
		for itemData in data:
			res.append(getEnumData(itemData,paths[1:],fieldOptions, method))
		return res
def getFieldDataFromPath(field_name, data):
	items = field_name.split(".")
	itemData = data
	for item in items:
		if item in itemData:
			itemData  = itemData[item]
		else:
			itemData = None

	return itemData

def getLayoutItem(layout,path):
	items = path.split(".")
	item_layout = layout
	for item in items:
		if item in item_layout:
			item_layout = item_layout[item]
		elif re.match("items\[(\d+)\]", item):
			index = int(re.match("items\[(\d+)\]", item).group(1))
			if "items" in item_layout:
				item_layout = item_layout["items"][index]
			else:
				raise LayoutDefineError
		else:
			item_layout[item] = {}
			item_layout = item_layout[item]
	return item_layout

def getLevelData(content,level=None):
	target_id = level
	if not level:
		target_id = content_objects_get(name="team").id
	for parent in content.parents:
		if parent.content_id == target_id:
			return parent

def getClient(action,service,content):
	from content.models import Client
	teamData = getLevelData(content)
	if teamData and not service.site_level:
		owner_id = teamData.owner_id
		if teamData.data["level"] > 0 and "$jobtypes" in teamData.data:
			jobtype_cfg = teamData.data["$jobtypes"]
			if str(service.id) in jobtype_cfg and str(action.id) in jobtype_cfg[str(service.id)]:
				jobtype_cfg = jobtype_cfg[str(service.id)]
				cfgItem = jobtype_cfg[str(action.id)]
				levelContent = cfgItem["level"]
				for parent in content.parents:
					if str(parent.id) in cfgItem["objs"]:
						levelContent = cfgItem["objs"][str(parent.id)]
						break
				owner_id = getLevelData(content,levelContent).owner_id
		clients = Client.objects.filter(data__teams__contains=[content.team_id], data__user=owner_id)
	else:
		clients = [client for client in Client.objects.filter(data__teams__contains=["all"], data__services__contains=[service.id])]
	if len(clients) > 0:
		client = clients[0]
		if "$number" not in client.data:
			return client
		for current in clients:
			if "$number" in current.data and current.data["$number"] > client.data["$number"]:
				client = current
			else:
				return current
		return client







def reconcileLayoutItem(srcItem,prefix,field_name):
	if "key" in srcItem:
		if srcItem["key"].startswith(prefix):
			srcItem["key"] = prefix + "." + field_name + srcItem["key"][len(prefix):]
	if "items" in srcItem:
		for item in srcItem["items"]:
			reconcileLayoutItem(item,prefix,field_name)

def getSelectSechdule(res,schedule, session, activity):
	start_time = activity.start_time
	if schedule == 1:
		schedule_str = str(start_time.weekday())
	elif schedule == 2:
		schedule_str = str(start_time.day)
	elif schedule == 3:
		schedule_str = str(start_time.month) + "-" + str(start_time.day)
	end_time = activity.end_time
	if session > 0:
		while start_time < end_time:
			session_end_time = start_time + timedelta(minutes=session)
			if schedule_str:
				session_str = schedule_str + " " + start_time.strftime("%H:%M") + "--" + session_end_time.strftime("%H:%M")
			if not session_str in res:
				res[session_str] = []
			res[session_str].append(activity.id)
			start_time = session_end_time
	else:
		if not schedule_str in res:
			res[schedule_str] = []
		res[schedule_str].append(activity.id)
	return res


def week_of_month(dt):
	first_day = dt.replace(day=1)
	return dt.isocarlendar()[1] - first_day.isocarlendar()[1]

def getTimeDelta(time_str):
	time_str = time_str.upper()
	hours = 0
	if time_str.find('PM') >= 0:
		hours = 12
	hour_str, min_str = time_str.strip("AM").strip("PM").split(":")
	hours = hours + int(hour_str)
	mins = int(min_str)
	return timedelta(hours=hours, minutes=mins)

def cleanLayout(data,field_name="", prefix=""):
	if type(data) == dict:
		res = {}
		for key in data:
			res[key.replace("$field",field_name).replace("$prefix",prefix)] = cleanLayout(data[key],field_name, prefix)
		return res
	if type(data) == list:
		res = []
		for item in data:
			res.append(cleanLayout(item, field_name, prefix))
		return res
	if type(data) in [str,unicode]:
		return data.replace("$field",field_name).replace("$prefix", prefix)
	return data

def setLayout(data, base_layout, field_name=""):
	prefix_name = ""
	if field_name.find(".") > 0:
		prefix_name = field_name.rsplit(".",1)[0]

	data = cleanLayout(data, field_name, prefix_name)
	if data:
		for key in data:
			item_layout = base_layout
			real_key = key.replace("$field",field_name).replace("$prefix",prefix_name)
			items = real_key.split(".")
			if type(items) == list and len(items) >= 2:
				for item in items[:len(items) - 1]:
					if item in item_layout:
						item_layout = item_layout[item]
					elif re.match("items\[(\d+)\]", item):
						index = int(re.match("items\[(\d+)\]", item).group(1))
						if "items" in item_layout:
							item_layout = item_layout["items"][index]
						else:
							raise LayoutDefineError
					elif item == "$append":
						new_item = {}
						item_layout.append(new_item)
						item_layout=new_item
					elif items[-1].startswith("$insert("):
						indexNum = int(items[-1][8:-1])
						new_item = {}
						item_layout.insert(indexNum, new_item)
						item_layout=new_item
					else:
						item_layout[item] = {}
						item_layout = item_layout[item]
			if items[-1] == "$append":
				item_layout.append(data[key])
			elif items[-1].startswith("$insert("):
				indexNum = int(items[-1][8:-1])
				item_layout.insert(indexNum, data[key])
			else:
				item = items[-1]
				if re.match("items\[(\d+)\]", item):
					index = int(re.match("items\[(\d+)\]", item).group(1))
					item_layout["items"][index] = data[key]
				else:
					item_layout[item] = data[key]
			# else:
			# 	item_layout[items[0]] = data[key]
	return base_layout

def filterObj(param,target, data):
	obj = getattr(target,param["$ref"])
	if "$filters" in param:
		if "$query" in param:
			query = param["$filters"][param["$query"]]
		else:
			query = param["$filters"]["default"]
		method = query["$method"]
		filter = getattr(obj, method)
		if "params" in query:
			params = query["$params"]
			for item in params:
				params[item] = parseObj(params[item], data)
			results = filter(**params)
		else:
			results = filter()
		res = []
		if "$item" in param:
			for result in results:
				item = {}
				for key in param["$item"]:
					item[key] = parseObj(param["$item"][key], result)
				res.append(item)
		return res
	return obj


def get_client_ip(request):
	x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
	if x_forwarded_for:
		ip = x_forwarded_for.split(',')[0]
	else:
		ip = request.META.get('REMOTE_ADDR')
	return ip


def merge_funcs(funcs,field_funcs):
	for key in field_funcs:
		if key == 'init':
			if "init" not in funcs:
				funcs["init"] = field_funcs["init"]
			else:
				for item in field_funcs["init"]:
					if item not in funcs["init"]:
						funcs["init"].append(item)
		else:
			funcs[key] = field_funcs[key]

def get_dict_path(properties, field_path):
	if field_path:
		items = field_path.split(".")
		item_data = properties
		if type(items) == list and len(items) >= 2:
			for item in items[:len(items) - 1]:
				if item in item_data:
					item_data = item_data[item]
				elif re.match("(\w+)\[(\d+)\]", item):
					item_name = item[:item.find("[")]
					index = int(re.match("\w+\[(\d+)\]", item).group(1))
					if item_name in item_data:
						item_data = item_data[item_name][index]
					else:
						raise DataPathError
		elif properties:
			if field_path not in properties:
				raise DataPathError
			item_data = properties[field_path]
	else:
		item_data = properties
	return item_data

def setDefaultPage(content,page,is_list):
	if is_list or page.content.name == content.content.name:
		if "page" in content.data:
			content.data["page"][page.security] = page.id
			for key in content.data["page"]:
				if key < page.security and content.data["page"] == page.id:
					content.data["page"].pop(key)
		else:
			content.data["page"] = {}
			content.data["page"][page.security] = page.id
	else:
		if "page" in content.data:
			if page.content.name in content.data["page"]:
				content.data["page"][page.content.name][page.security] = page.id
			else:
				content.data["page"][page.content.name] = {page.security: page.id}
		else:
			content.data["page"] = {page.content.name: {page.security: page.id}}
	content.save()

def setAllDataParents():
	from content.models import ContentData
	contentDatas = ContentData.objects.all()
	content_list = {}
	for data in contentDatas:
		content_list[data.id] = data

	for data in contentDatas:
		parents = []
		parent = data.parent_id
		while parent:
			parents.append(parent)
			parent = content_list[parent].parent_id
		data.data["parents"] = parents
		data.save()

def getFieldName(name):
	return name.lower().replace(" ","_")

def getFieldLangName(field_data, language):
	lang_dict = {}
	langs_data = field_data
	if "langs" in field_data:
		langs_data = field_data["langs"]
	if type(langs_data) == list:
		for lang_item in langs_data:
			lang_dict[lang_item["lang_select"]] = lang_item
	if len(lang_dict) > 0:
		if language in lang_dict:
			return lang_dict[language]["name_x_contentfield_x_0"]
		elif "English" in lang_dict:
			return lang_dict["English"]["name_x_contentfield_x_0"]
	else:
		if "name_x_contentfield_x_0" in field_data:
			return field_data["name_x_contentfield_x_0"]


def getTimeLine(gap_duration, target_time):
	start_gap = gap_duration
	after = False
	if "after" in start_gap:
		after = start_gap.pop("after")
	start_gap = timedelta(**start_gap)
	if after:
		start_time = target_time + start_gap
	else:
		start_time = target_time - start_gap
	return start_time

def getBulkFieldsData(fieldContents, data_list , content, platformData=None):
	from content.models import ContentData
	refData={}
	for name in fieldContents:
		if fieldContents[name].getter:
			getRefKey(refData, fieldContents[name].getter)
	field_name = None
	object_id_list = [int(data.object_id) for data in data_list]

	preClazz = None
	for key in refData:
		content_list = [data for data in data_list]
		index_list = [data.id for data in data_list]
		items = key.split(".")
		clazz = ContentData
		# preClazz = ContentData
		# target_list = {}
		# query_str = ""
		res = dict(zip(index_list,index_list))
		for item in items[1:]:
			try:
				field_name = item
				field = clazz._meta.get_field(item)
				tempRes = {}
				if field.related_model and issubclass(field.related_model, models.Model):
					field_name = None
					clazz =field.related_model
					query_str = field.related_query_name()
					objs = clazz.objects.filter(**{query_str + "__in": content_list}).order_by(query_str + "__id")
					for obj in content_list:
						tempRes[obj.id] = getattr(obj,item+"_id")
					for id in res:
						try:
							if res[id] in tempRes:
								res[id] = tempRes[int(res[id])]
						except Exception as e:
							print e.message

					content_list = objs

			except FieldDoesNotExist:
				if item == "target":
					field_name = None
					tempRes={}
					for obj in content_list:
						tempRes[obj.id] = int(obj.object_id)
					for id in res:
						res[id] = tempRes[id]
					if not content.target:
						raise ValueError("Wrong reference for platform type content")
					clazz = content.target.model_class()
					# content_list = [target for target in clazz.objects.filter(id__in = object_id_list)]
					content_list = [item for item in content.get_objs(ids=object_id_list,platformData = platformData)]


		tempRes = {}
		for obj in content_list:
			tempRes[obj.id] = obj

		for id in res:
			if res[id]:
				if res[id] in tempRes:
					res[id] = tempRes[res[id]]
					if field_name and res[id]:
						res[id] = getattr(res[id], field_name)
				else:
					res[id] = None
		refData[key] = res
	return refData




def getRefKey(refData, defData):
	for key in defData:
		if key == "$ref":
			refData[defData[key]] = "value"
		else:
			if type(defData[key]) == dict:
				getRefKey(refData,defData[key])

def getFieldTitleFromData(field_name,content_name,fields_data,language):
	index = None

	if field_name.find(FIELD_SEPARATOR) > 0:
		field_name,content_name,index = field_name.split(FIELD_SEPARATOR)
	else:
		if field_name in fields_data and content_name in fields_data[field_name] and \
			"default" in fields_data[field_name][content_name]:
			index = fields_data[field_name][content_name]["default"]
	if not index:
		return field_name, field_name
	default_data = None
	if index in fields_data[field_name][content_name]:
		data = fields_data[field_name][content_name][index]
		if "langs" in data:
			data = data["langs"]
		if type(data) == dict:
			return field_name, FIELD_SEPARATOR.join([field_name,content_name,index])
		for lang_data in data:
			try:
				if lang_data["lang_select"] == language:
					return lang_data[FIELD_TITLE],FIELD_SEPARATOR.join([field_name,content_name,index])
				if lang_data["lang_select"] == "English":
					default_data = lang_data
			except Exception as e:
				print e.message

		if default_data:
			return default_data[FIELD_TITLE], FIELD_SEPARATOR.join([field_name,content_name,index])
	return field_name, FIELD_SEPARATOR.join([field_name,content_name,index])

def getFieldTitle(field_name,content_name,contentData,language):
	# parents = contentData.parents
	# parents.reverse()
	# parents.append(contentData)
	#
	# fields_data = {}
	# for parent in parents:
	# 	if "fields" in parent.data:
	# 		merge(fields_data, parent.data["fields"])
	fieldTitle, fieldId = getFieldTitleFromData(field_name, content_name,contentData.getFieldsData(),language)
	return fieldTitle

def getField(content,field):
	if field.find(FIELD_SEPARATOR) > 0:
		fieldname = field.split(FIELD_SEPARATOR)[0]
		contentField = content.field(fieldname)
		contentField.name = field
	else:
		contentField = content.field(field)
	return contentField


def changeFieldSeparator():
	from content.models import ContentData
	contentDatas = ContentData.objects.filter(data__has_key="fields")
	for contentData in contentDatas:
		fields_data = contentData.data["fields"]
		contentData.data["fields"] = json.loads(json.dumps(fields_data).replace("-",FIELD_SEPARATOR))
		contentData.save()



def changeItemSeparator(fieldData):
	if type(fieldData) == list:
		for i in range(0, len(fieldData)):
			fieldData[i] = changeItemSeparator(fieldData[i])
		return fieldData
	if type(fieldData) == dict:
			res = {}
			for key in fieldData:
				newKey = key
				if key.find("-") > 0:
					newKey = FIELD_SEPARATOR.join(key.split("-"))
				res[newKey] = changeItemSeparator(fieldData[key])
			return res

	return FIELD_SEPARATOR.join(fieldData.split("-"))

def isSystemField(fields_data, fieldItems):
	if fieldItems[0] in fields_data:
		if fieldItems[1] in fields_data[fieldItems[0]]:
			if fieldItems[2] in fields_data[fieldItems[0]][fieldItems[1]]:
				field_data = fields_data[fieldItems[0]][fieldItems[1]][fieldItems[2]]
				if DEFAULT_FIELD in field_data:
					return field_data[DEFAULT_FIELD]
	return False

def replace_str(data, scr_str, dst_str):
	if type(data) in [str, unicode]:
		return data.replace(scr_str, dst_str)
	if type(data) == list:
		res = []
		for item in data:
			res.append(replace_str(item,scr_str,dst_str))
		return res
	if type(data) == dict:
		res = {}
		for key in data:
			res[key.replace(scr_str,dst_str)] = replace_str(data[key],scr_str,dst_str)
		return res
	return data

def is_jsonable(x):
	try:
		json.dumps(x)
		return True
	except:
		return False

def get_field_template(field, contentData=None, targetData=None, properties=None, fields=None, field_dicts={}, unique_name=None,
					   language=None):
	rootField = field_objects_get(field.field_id)
	getterContent = content_objects_get(name="getter")
	template = rootField.template
	if field.name not in field_dicts:
		field_dicts[field.name] = field
	contentFields = []
	if rootField.is_list_field:
		field_list = []

		fieldsData =None
		if contentData:
			# field_data = contentData.getFieldData(field)
			field_data = contentData.getFieldDataFromConfig(field)
			fieldsData = contentData.getFieldsData()
			# if field_data and "fields" in field_data and "select_field_x_none_x_0" in field_data:
			if field_data and "fields" in field_data:
				field_list = field_data["fields"]

		if fields:
			field_list = fields
		field_list_template = ""
		#rawField = field_objects_get(field.field_id)

		rawContent = content_objects_get(id=contentData.content_id)
		content_list = False
		item_var = "$height"
		total = 0
		if "width" in rootField.schema["items"]["properties"]:
			content_list = True
			item_var = "$width"
			minium = 0
			zero_size = 0
			for item in field_list:
				if "width" in item:
					total += int(item["width"])
					if minium == 0:
						minium = int(item["width"])
					elif minium > int(item["width"]):
						minium = int(item["width"])
				else:
					zero_size += 1
			total += zero_size * minium
			if total == 0:
				minium = 100

		for item in field_list:
			if type(item) ==dict:
				if "field" in item:
					field_full_name = item["field"]
				else:
					field_full_name = getFieldId(fieldsData, item["title"])
			elif type(item) in [str,unicode]:
				field_full_name = item
			tags = []
			if "tags" in item:
				tags = item["tags"]
			field_item_template = rootField.get_item_template(tags)
			field_items= field_full_name.split(FIELD_SEPARATOR)
			field_name = field_items[0]
			if len(field_items) == 3:
				content_name = field_items[1]
			else:
				content_name = rawContent.name
			field_item = ""
			if content_list:
				if "width" in item:
					field_item = item["width"]
				else:
					field_item = minium
			elif "height" in item :
				if int(item["height"]) > 0:
					field_item = "height:" + str(item["height"]) + "%"
				else:
					field_item = "height:auto"
			# if "width" in item:
			# 	item_var = "$width"
			# 	field_item = item["width"]
			# elif "height" in item:
			# 	item_var = "$height"
			# 	field_item = item["height"]
			# else:
			# 	field_item = 0
			if field_full_name in field_dicts:
				contentField = field_dicts[field_full_name]
			else:
				if field.content and field.content == getterContent:
					contentField = contentData.target.content.field(field_name)
				else:
					contentField = contentfield_objects_get(field_name,content_name=content_name)
				field_dicts[field_full_name] = contentField
			# if contentField.content:
			# 	content_name = contentField.content.name
			# else:
			# 	content_name = "none"
			contentField.name = field_full_name

			contentFields.append(contentField)
			field_title = getFieldTitle(field_full_name, content_name, contentData, language)
			field_template_str = field_item_template.replace("$field", field_full_name).replace("$unique",
																								unique_name).replace(
				"$title", field_title)
			# if field_item:
			field_template_str = field_template_str.replace(item_var, str(field_item)).replace("$unique",
																								   unique_name)
			if contentField.field_id and field_objects_get(contentField.field_id).item_template and len(
					field_objects_get(contentField.field_id).item_template) > 0:
				if field.is_list:
					item_template = contentField.get_item_template().replace("$field", "value").replace("$unique",
																										unique_name)
				else:
					item_template = contentField.template_str(unique_name,contentData=contentData,fieldsData=fieldsData)
			else:
				if field.is_list:
					item_template = contentField.get_item_template().replace("$field", "value").replace("$unique",
																										unique_name)
				else:
					# item_template = contentField.get_item_template().replace("$field", contentField.name).replace("$unique",self.unique_name)
					item_template = contentField.template_str(unique_name, properties=properties,contentData=contentData,fieldsData=fieldsData)
			field_template_str = field_template_str.replace("{{" + field_full_name + "}}", item_template).replace(
				"$unique", unique_name).replace("$title",field_title)
			field_list_template += field_template_str
		field_template = template.replace("$field", field.name).replace("{{$item_list_field}}",
					field_list_template).replace("$unique",unique_name)
		# field_template = field.field.template.replace("$field",field.name)
	template = field_template
	return template


def get_field_template_funcs(contentField, unique_name=None, contentData=None, targetData=None, fields=None, properties=None, field_dicts={}):
	funcs = contentField.template_funcs(unique_name)
	if "init" not in funcs:
		funcs["init"] = []
	if fields:
		field_list = fields
	else:
		field_data = contentData.getFieldData(contentField)
		field_list = field_data["select_field_x_none_x_0"]
	# content_name = contentData.content.name
	content_name = content_objects_get(contentData.content_id).name
	rootField = field_objects_get(contentField.field_id)
	if rootField.is_list_field:
		for item in field_list:
			if type(item) == dict:
				full_field_name = item["field"]
			elif type(item) in[str,unicode]:
				full_field_name = item
			field_name = full_field_name.split(FIELD_SEPARATOR)[0]
			if field_name in field_dicts:
				field = field_dicts[field_name]
			else:
				getterContent = content_objects_get(name="getter")
				if contentField.content and contentField.content == getterContent:
					field = contentData.target.content.field(field_name)
				else:
					field = contentfield_objects_get(field_name,content_name=content_name)
				field_dicts[field_name] = contentField
			field.name = full_field_name
			rawField = field_objects_get(field.field_id)
			if rawField.is_list_field and rawField.item_template_func:
				template_funcs = {"item_" + field.name + "_func": rawField.item_template_func}
			else:
				template_funcs = field.template_funcs(unique_name, properties=properties)
			setFuncs(funcs, template_funcs)
	return funcs

def cleanData(data):
	if type(data) == dict:
		pop_keys = []
		for key in data:
			if data[key] == None:
				pop_keys.append(key)
			else:
				data_clean = cleanData(data[key])
				if not data_clean == None:
					data[key] = data_clean
				else:
					pop_keys.append(key)
		for pop_key in pop_keys:
			data.pop(pop_key)
	elif type(data) == list:
		data_list =[]
		for data_item in data:
			data_clean = cleanData(data_item)
			if data_clean:
				data_list.append(data_clean)
		data = data_list
	return data



def getLanguage(request):
	data = json.loads(request.body)
	language = None
	if "language" in data:
		language = data["language"]
		if language in LANGUAGES:
			language = LANGUAGES[language]
	return language


def isCompSchedule(schedule, target_schedule):
	if "start_time" in schedule and "end_time" in schedule:
		if "start_time" in target_schedule and "end_time" in target_schedule:
			if schedule["start_time"] >= target_schedule["end_time"]:
				return True
			if target_schedule["start_time"] >= schedule["end_time"]:
				return True
	#overlap start time and end time, check days or weekdays
	if "days" in schedule and "days" in target_schedule:
		if set(schedule["days"]).isdisjoint(target_schedule["days"]):
			return True
		if "months" in schedule and "months" in target_schedule:
			if set(schedule["months"]).isdisjoint(target_schedule["months"]):
				return True
	if "weekdays" in schedule and "weekdays" in target_schedule:
		if set(schedule["weekdays"]).isdisjoint(target_schedule["weekdays"]):
			return True
		if "months" in schedule and "months" in target_schedule:
			if set(schedule["months"]).isdisjoint(target_schedule["months"]):
				return True
	if "weeks" in schedule and "weeks" in target_schedule:
		if set(schedule["weeks"]).isdisjoint(target_schedule["weeks"]):
			return True
	if "months" in schedule and "months" in target_schedule:
		if set(schedule["months"]).isdisjoint(target_schedule["months"]):
			return True

	return False


def getFieldDataFromCfg(field,fields_data):
	if type(field) in [str, unicode]:
		if field.find(FIELD_SEPARATOR) > 0:
			fieldItems = field.split(FIELD_SEPARATOR)
			if fieldItems[0] in fields_data and fieldItems[1] in fields_data[fieldItems[0]]:
				return fields_data[fieldItems[0]][fieldItems[1]][fieldItems[2]]
		else:
			if field in fields_data and "none" in fields_data[field]:
				return fields_data[field]["none"]["0"]
	else:
		if field.name.find(FIELD_SEPARATOR) > 0:
			fieldItems = field.name.split(FIELD_SEPARATOR)
			if fieldItems[0] in fields_data and fieldItems[1] in fields_data[fieldItems[0]]:
				return fields_data[fieldItems[0]][fieldItems[1]][fieldItems[2]]
		else:
			if field.content_id:
				content_name = content_objects_get(field.content_id).name
			else:
				content_name = "none"
			if field.name in fields_data and content_name in fields_data[field.name] and "default" in \
					fields_data[field.name][content_name]:
				default = fields_data[field.name][content_name]["default"]
				return fields_data[field.name][content_name][default]

def getDefaultFieldId(field, fields_data):
	if field.content:
		content_name = content_objects_get(field.content_id).name
	else:
		content_name = "none"
	if field.name in fields_data and content_name in fields_data[field.name] and "default" in \
			fields_data[field.name][content_name]:
		default = fields_data[field.name][content_name]["default"]
		return FIELD_SEPARATOR.join([field.name,content_name,default])
	else:
		return field.name

def transferData(app):
	contents = ContentType.objects.filter(app_label=app)
	for content in contents:
		model = content.model_class()
		if model:
			objs = model.objects.using('local').all()
			for obj in objs:
				try:
					obj.save(using="default")
				except:
					print obj.__class__.__name__ + ":" + str(obj.id)



def setupTemplateFields():
	from content.models import Template
	templates = Template.objects.all()
	for template in templates:
		fields = template.fields.all()
		template.data = {}
		template.data["fields"] = [field.id for field in fields]
		template.save()

def setupHooks():
	from content.models import ContentData
	data_list = ContentData.objects.all()
	for itemData in data_list:
		hooks = [hook.id for hook in itemData.hooks.all()]
		itemData.data["hooks"] = hooks
		itemData.save()


def setupActionOptions():
	from content.models import Action
	actions = Action.objects.all()
	for action in actions:
		options = [option.id for option in action.options.all()]
		action.data["options"] = options
		action.save()

def setupActionBlockers():
	from content.models import Action
	actions = Action.objects.all()
	for action in actions:
		blockers = [blocker.id for blocker in action.blockers.all()]
		action.data["blockers"] = blockers
		action.save()

def setupActionRoles():
	from content.models import Action
	actions = Action.objects.all()
	for action in actions:
		roles = [role.id for role in action.roles.all()]
		action.data["roles"] = roles
		action.save()


def setupPages():
	from content.models import ContentData
	data_list = ContentData.objects.all()
	for itemData in data_list:
		pages = [page.id for page in itemData.pages.all()]
		itemData.data["pages"] = pages
		itemData.save()

def setupGetters():
	from content.models import ContentData
	data_list = ContentData.objects.all()
	for itemData in data_list:
		getters = [getter.id for getter in itemData.getters.all()]
		itemData.data["getters"] = getters
		itemData.save()


def setupProfile():
	from content.models import ContentData, Profile
	profiles = Profile.objects.all()
	profileDatas = ContentData.objects.filter(content__name="profile")
	profile_list = {}
	for profile in profiles:
		profile_list[str(profile.id)] = profile
	for profileData in profileDatas:
		if profileData.object_id in profile_list:
			profile = profile_list[profileData.object_id]
			for key in profileData.data:
				if not key == "parents":
					profile.data[key] = profileData.data[key]
			roles = profile.user.roles.all()
			profile.data["$roles"] = [role.id for role in roles]
			profile.save()

def setupRoleMembers():
	from content.models import Role
	roles = Role.objects.filter(static=True)
	for role in roles:
		users = [user.id for user in role.members.all()]
		role.data["members"] = users
		role.save()


def setupRoleData():
	from content.models import ContentData
	roles = get_dyn_roles()
	role_datas = ContentData.objects.filter(content__name="role")
	role_dict = {}
	for roleData in role_datas:
		role_dict[roleData.object_id] = roleData
	siteData = get_website_data()
	roleContent = content_objects_get(name="role")
	for role in roles:
		if str(role.id) not in role_dict:
			roleData = ContentData(content=roleContent,object_id=str(role.id),status=roleContent.operating_status,parent=siteData)
			roleData.data["parents"]=[siteData.id]
			roleData.save()


def setPermissions():
	pass


def getActionCore(data):
	if "core" in data:
		return data["core"]
	from content.models import ContentData
	targetData = data["target"]
	while targetData["content"] == "action":
		targetData=targetData["target"]

	while "id" not in targetData:
		targetData=targetData["target"]


	if not targetData["content"] == "action":
		content = content_objects_get(name=targetData["content"])
		if content.name == "website":
			core = get_website_data()
		else:
			core = ContentData.objects.get(id=targetData["id"])
	data["core"] = core
	return core

def prepareColumns(data):
	columns_data = data.pop("columns")
	field_columns = []
	for column_data in columns_data:
		try:
			column_field = json.loads(column_data)["id"]
		except ValueError as e:
			column_field = column_data
		field_columns.append(column_field)
	return field_columns

def prepareField(data):
	try:
		return json.loads(data)["id"]
	except ValueError as e:
		return data

def getContextContent(context,field):
	page = None
	from content.models import ContentData
	content = None
	action = None
	if "content" in context and "id" in context:
		if context["content"] == "action":

			field_action = action_objects_get(context["id"])
			targetData = context["target"]
			while "id" not in targetData:
				targetData = targetData["target"]
			content_name = targetData["content"]
			content_id = targetData["id"]

			if field_action.name == "Field Configure":
				contentField = ContentData.objects.get(content__name="contentfield", id=context["target"]["id"]).target
				content = content_objects_get(id=contentField.content_id)
			elif field_action.name == "Field Customise":
				field_content = context["params"].split(FIELD_SEPARATOR)[1]
				if not field_content == 'none':
					content = content_objects_get(name=field_content)
				else:
					content = None
			else:
				content_name = context["target"]["content"]
				content_id = context["target"]["id"]
				field_content = field.split(FIELD_SEPARATOR)[1]
				if field_content == "none":
					field_content = "profile"
				content = content_objects_get(name = field_content)
				action = field_action
			targetData = ContentData.objects.get(content__name=content_name, id=content_id)
		else:
			targetData = ContentData.objects.get(content__name=context["content"],id=context["id"])
	else:
		if "target" in context:
			if "content" in context["target"] and "id" in context["target"]:
				targetData = ContentData.objects.get(content__name=context["target"]["content"],id=context["target"]["id"])
	if not content:
		if "page" in context:
			page = page_objects_get(id = context["page"])
			if page.action_id:
				action = action_objects_get(page.action_id)
			content = content_objects_get(id = page.content_id)
		elif context["content"] == "getter":
			content = targetData.target.content
			targetData = targetData
		elif "field" in context:
			content_name = context["field"].split(FIELD_SEPARATOR)[1]
			if content_name == "none":
				content_name = "profile"
			content = content_objects_get(name = content_name)
		else:
			content = content_objects_get(name=context["content"])

	return targetData,content,action,page

def getOldAccessLevel(user,team):
	user_access = {}
	access_list = ["authenticated","member","manager","owner","staff"]
	for role in access_list:
		user_access[role] = False
	user_access["staff"] = user.is_staff
	if user.is_authenticated():
		user_access["authenticated"] = True
	if team and team.is_member(user):
		user_access["member"] = True
	if team and team.is_manager(user):
		user_access["manager"] = True
	is_staff = user.is_staff
	return user_access

def getSingleFieldContentList(targetData,field_columns, context,action,content,language):
	from content.models import ContentData
	if not targetData:
		context = context["target"]
		targetData = ContentData.objects.get(content__name=context["content"], id=context["id"])
	field_name = field_columns[0]
	# contentField = targetData.content.field(field_name)
	content_name = None
	if content:
		content_name = content.name
	contentField = contentfield_objects_get(field_name, content_name=content_name)
	if contentField.list_getter:
		data_list = parseObj(contentField.list_getter,
		                     {"content": targetData, "columns": field_columns, "context": context, "action": action,
		                      "language": language})
		res = {}
		res["result"] = True
		res["data"] = data_list
		return res


def getContentListDataCore(targetField,targetData,content,context, team):
	from content.models import ContentData
	coreList = None
	if targetField and targetField.list_getter and len(targetField.list_getter) > 0:
		datalist, coreList = generateObj(targetField.list_getter, {"content": targetData})
		#targetPage = targetData.getFieldDataFromConfig(targetField.name)["page"]
	else:
		if team:
			teamData = ContentData.objects.get(content__name="team", object_id=str(team.id),is_deleted=False)
			if "children_teams" in teamData.data:
				teams = teamData.data["children_teams"]
			else:
				teams = []
			teams.append(team.id)
			# get all origin content
			datalist = ContentData.objects.filter(team__id__in=teams, content=content,
			                                      data__parents__contains=[targetData.id],is_deleted=False)
		else:
			if content.name in ["category"]:
				datalist = targetData.children.filter(content=content, is_deleted=False)
			else:
				datalist = ContentData.objects.filter(content=content,is_deleted=False)

	if targetData and "getters" in targetData.data:
		# filters = targetData.getters.filter(content=content,is_list=True)
		filters = [getter_objects_get(getter_id) for getter_id in targetData.data["getters"]]
		filters = filter(lambda x: x.content_id == content.id and x.is_list, filters)
		# clz = content.target.model_class()
		for getter in filters:
			if context["content"] == "getter":
				kwargs = parseObj(getter.getter, {"content": targetData.parent})
			else:
				kwargs = parseObj(getter.getter, {"content": targetData})
			target_list = content.query(**kwargs)
			target_list_ids = [str(obj.id) for obj in target_list]
			datalist = datalist.filter(object_id__in=target_list_ids)

	obj_ids = [item.object_id for item in datalist]
	#	contentType = content.target
	#	coreList = contentType.model_class().objects.filter(id__in=obj_ids)
	platformData = None
	if content.platform:
		if content.platform.is_shared:
			platformData = targetData.getPlatformData(content.platform_id)
		else:
			platformData = targetData.getProfilePlatform(content.platform_id)

	if not coreList:
		coreList = [core for core in content.get_objs(obj_ids, platformData)]

	return datalist,coreList,platformData

def getExtendSystemFields(targetData,field_columns,columns):
	fields_data = targetData.getFieldsData()
	extend_fields = []
	system_fields = {}
	for field_column in field_columns:
		fieldItems = field_column.split(FIELD_SEPARATOR)
		if len(fieldItems) == 1:
			columns.append(field_column)
		else:
			if isSystemField(fields_data,fieldItems):
				columns.append(fieldItems[0])
				system_fields[field_column] = fieldItems[0]
			else:
				extend_fields.append(field_column)
	return extend_fields,system_fields

def reset(name):
	global ACTIONS,CONTENTFIELDS,CONTENTS,FIELDS
	if name == "action":
		ACTIONS=set_action_objects()
	if name == "contentfield" :
		CONTENTFIELDS = set_content_fields()
	if name == "content":
		CONTENTS = set_content_objects()
	if name == "fields" :
		FIELDS = set_field_objects()

def getTeamData(content):
	teamData = None
	teamContent = content_objects_get(name="team")
	if content.content_id == teamContent.id:
		teamData = content
	elif content.team_id:
		for parent in content.parents:
			if parent.content_id == teamContent.id and parent.object_id == str(content.team_id):
				teamData = parent
				break
	return teamData

def set_profile_data(user,profile_data_list,team=None,teamData=None):
	from content.models import ContentData
	profileContent = content_objects_get(name="teamprofile")
	profileData, create = ContentData.objects.get_or_create(team=team, content=profileContent,
	                                                        object_id=str(user.profile.id),
	                                                        status=profileContent.operating_status,
	                                                        parent=teamData)

	for key in profile_data_list:
		profileData.data[key] = profile_data_list[key]
		profile = user.profile
		profile.data[key] = profile_data_list[key]
		profile.save()
	profileData.save()


def getContentList(data, user, language):
	from content.models import Team,ContentData
	context = data
	field = None
	targetPage = None
	fields = []
	field_columns = prepareColumns(data)

	page = None
	columns = []
	querystr = None
	if "querystr" in context:
		querystr = context["querystr"]

	if "field" in context:
		field = context["field"]
		targetField = contentfield_objects_get(name=field.split(FIELD_SEPARATOR)[0])
	else:
		targetField = None

	targetData, content, action, page = getContextContent(context, field)

	team = None
	if "team" in context:
		team = Team.objects.get(id=context["team"])

	res = {"result": True}
	res["data"] = []
	if field:
		res["field"] = field

	# field as content list, link to different content data as a field and using list_getter func to get linking objs
	if len(field_columns) == 1:
		content_res = getSingleFieldContentList(targetData, field_columns, context, action, content, language)
		if content_res:
			return content_res

	if page and page.getter:
		if not targetData:
			context = context["target"]
			targetData = ContentData.objects.get(content__name=context["content"], id=context["id"])
		datalist = parseObj(page.getter,
		                    {"content": targetData, "columns": columns, "context": context, "action": action,
		                     "language": language})
		res["result"] = True
		res["data"] = datalist
		return res

	if targetField and targetField.list_getter and len(targetField.list_getter) > 0 and "raw" in targetField.list_getter:
		res["result"] = True
		res["data"] = generateObj(targetField.list_getter, {"content": targetData,"columns":field_columns,"field":field})
		return res
	datalist, coreList, platformData = getContentListDataCore(targetField, targetData, content, context, team)
	coresDict = {}
	for core in coreList:
		coresDict[str(core.id)] = core

	extend_fields, system_fields = getExtendSystemFields(targetData, field_columns, columns)

	contentFields = []
	itemsResult = {}
	columns = []
	for field_name in field_columns:
		name = field_name.split(FIELD_SEPARATOR)[0]
		contentField = contentfield_objects_get(name=name, content_name=content.name)
		if contentField.list_getter and len(contentField.list_getter) > 0:
			fieldResult = parseObj(contentField.list_getter,
			                       {"content_list": datalist, "target_list": coreList, "field_name": name})
			merge(itemsResult, fieldResult)
		else:
			contentFields.append(contentField)
			columns.append(field_name)

	target_model = None
	if content.target:
		target_model = content.target.model
	owner_path = None
	content_data = content.data
	if "$owner" in content.data:
		owner_path = content.data["$owner"]

	field_contents = {}

	# for field in fields:
	# 	field_contents[field.name] = field

	for field in contentFields:
		field_contents[field.name] = field

	fieldsData = getBulkFieldsData(field_contents, datalist, content, platformData=platformData)

	content_name = content.name

	access_level = targetData.getAccessLevel(user=user, team=team)

	if not targetData or content_objects_get(targetData.content_id).name in ["team", "website"]:
		for contentData in datalist:
			# if contentData.is_owner(user, owner_path=owner_path):
			# 	user_access["owner"] = True
			if contentData.object_id in coresDict:
				target = coresDict[contentData.object_id]
				if contentData.security <= access_level or contentData.is_owner(user,
				                                                                owner_path=owner_path) or user.is_staff:
					if len(contentFields) > 0:
						item = contentData.getData(columns, target, fields=fields, contentfields=contentFields,
						                           target_model=target_model, content_data=content_data,
						                           content_name=content_name, fields_data=fieldsData, language=language)
						if contentData.id in itemsResult:
							for key in itemsResult[contentData.id]:
								item[key] = itemsResult[contentData.id][key]
					else:
						item = itemsResult[contentData.id]
					itemContext = {"content": content_name, "id": contentData.id}
					if content.name == "team":
						itemContext["team"] = contentData.object_id
					if team:
						itemContext["team"] = team.id
					if action:
						item["context"] = {"content": "action", "id": action.id, "target": itemContext}
					else:
						item["context"] = itemContext
					if targetPage:
						item["context"]["page"] = targetPage.id
					for field_item in system_fields:
						if system_fields[field_item] in item:
							item[field_item] = item[system_fields[field_item]]
						else:
							item[field_item] = None
					for field_item in extend_fields:
						if field_item in contentData.data:
							item[field_item] = contentData.data[field_item]
					res["data"].append(item)

	else:
		# defined by accessor security
		for contentData in datalist:
			item = contentData.getData(field_columns, coresDict[contentData.object_id], target_model=target_model,
			                           content_data=content_data)
			item["context"] = {"content": contentData.content.name, "id": contentData.id}
			if content.name == "team":
				item["context"]["team"] = contentData.object_id
			if team:
				item["context"]["team"] = team.id
			if targetPage:
				item["context"]["page"] = targetPage.id
			item["target"] = context
			res["data"].append(item)

	if querystr:
		query_res = []
		for item in res["data"]:
			query_condition = querystr.format(**item)
			if eval(query_condition):
				query_res.append(item)
		res["data"] = query_res

	return res


def prepareMenuActions(contentData, actions, step_actions, contents_dict, dataContext, language=None, actions_data=None):
	action_id_list = []
	if step_actions:
		if "items" not in actions:
			actions["items"] = []
		for action in step_actions:
			if action.id not in action_id_list and action.visible:
				action_id_list.append(action.id)
				actionItem = {}
				actionItem["name"] = action.name
				if actions_data and str(action.id) in actions_data:
					action_data = actions_data[str(action.id)]
					if language and "langs" in action_data:
						for lang_item in action_data["langs"]:
							if lang_item["lang_select"] == language:
								actionItem["name"] = lang_item["name_x_contentaction_x_0"]

				actionItem["id"] = action.id
				actionItem["content"] = "action"
				actionItem["options"] = []
				if "options" in action.data:
					for option_id in action.data["options"]:
						option = action_objects_get(option_id)
						optionItem = {}
						optionItem["name"] = option.name
						optionItem["id"] = option.id
						optionItem["content"] = "action"
						optionItem["target"] = dataContext
						actionItem["options"].append(optionItem)
				actionItem["target"] = dataContext
				if not action.pass_on:
					if action.content_id == contentData.content_id:
						if action.is_initializer and action.content_id not in contentData.hooks:
							if not action.content_id in contents_dict:
								contents_dict[action.content_id] = [actionItem]
							else:
								contents_dict[action.content_id].append(actionItem)
						else:
							actions["items"].append(actionItem)
					else:
						if not action.content_id in contents_dict:
							contents_dict[action.content_id]=[actionItem]
						else:
							contents_dict[action.content_id].append(actionItem)
				else:
					actions["items"].append(actionItem)

def replaceCatData(item,data_dict,config={}, copy={}):
	if "children" in item:
		for child in item["children"]:
			replaceCatData(child,data_dict,config=config, copy=copy)
	if str(item["id"]) in data_dict:
		item["id"] = data_dict[str(item["id"])]
		for key in config:
			item[key] = config[key]
		for key in copy:
			if key in item:
				item[copy[key]] = item[key]


def addChildren(data_dict,item, children):
	item_id = str(item.id)
	item_data = {"id": item.id, "name":item.name}
	if item_id in data_dict:
		item_list = data_dict[item_id]
		child_list = []
		for child in item_list:
			addChildren(data_dict,child,child_list)
		item_data["children"] = child_list
	children.append(item_data)

def createCatergoryData():
	from content.models import Category,ContentData
	siteData = get_website_data()
	category_content = content_objects_get(name='category')
	category_list = siteData.children.filter(content=category_content)
	catdata_dict = {}
	for cat_data in category_list:
		catdata_dict[cat_data.object_id] = cat_data
	category_obj_ids = [int(catData.object_id) for catData in category_list]
	category_objs = Category.objects.filter(id__in = category_obj_ids)
	for category in category_objs:
		cat_data = catdata_dict[str(category.id)]
		cat_list = Category.objects.filter(id__in=category.data["$children"])
		cat_dict={}
		cat_tree={}
		for cat in cat_list:
			cat_dict[cat.id] = cat
			if cat.parent_id:
				if cat.parent_id in cat_tree:
					cat_tree[cat.parent_id].append(cat.id)
				else:
					cat_tree[cat.parent_id] = [cat.id]
		createCatData(cat_data,cat_tree)
		print cat_tree

def createCatData(cat_data,cat_tree):
	from content.models import Category, ContentData
	category_content = content_objects_get(name='category')
	object_id = cat_data.object_id
	if int(object_id) in cat_tree:
		cat_list = cat_tree[int(object_id)]
		for cat_id in cat_list:
			newCatData = ContentData(content=category_content, object_id=str(cat_id),parent=cat_data,status=category_content.start_status)
			newCatData.save()
			newCatData.setParent(cat_data)
			createCatData(newCatData,cat_tree)

def getTargetID(data):
	if "id" in data:
		return data["id"]
	elif "target" in data:
		return getTargetID(data["target"])



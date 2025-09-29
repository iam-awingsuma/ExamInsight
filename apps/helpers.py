import os
import re
import uuid
import re
from colorama import Fore, Style
from apps.authentication.models import Users
from apps.config import Config
from marshmallow import ValidationError
from apps.messages import Messages
from functools import wraps
from urllib.parse import urlencode
from flask import request, url_for
from sqlalchemy import or_, String
from uuid import uuid4
import datetime, time
message = Messages.message

Currency = Config.CURRENCY
PAYMENT_TYPE = Config.PAYMENT_TYPE
STATE = Config.STATE


regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')

def get_ts():
    return int(time.time())

def password_validate(password):
    """ password validate """
    msg = ''
    while True:
        if len(password) < 6:
           msg = "Make sure your password is at lest 6 letters"
           return msg
        elif re.search('[0-9]',password) is None:
            msg = "Make sure your password has a number in it"
            return msg
        elif re.search('[A-Z]',password) is None: 
            msg = "Make sure your password has a capital letter in it"
            return msg
        else:
            msg = True
            break
        
    return True

def emailValidate(email):
    """ validate email  """
    if re.fullmatch(regex, email):
        return True
    else:
        return False

# santise file name
def sanitise_fille_name(value):
    """ remove special char  """
    return value.strip().lower().replace(' ', '_').replace('(', '').replace(')', '').replace(',', '').replace('=','_').replace('-', '_').replace('#', '')

def createFolder(folder_name):
    """ create folder for save csv """
    if not os.path.exists(f'{folder_name}'):
        os.makedirs(f'{folder_name}')

    return folder_name

def uniqueFileName(file_name):
    """ for Unique file name"""
    file_uuid = uuid.uuid4()
    IMAGE_NAME = f'{file_uuid}-{file_name}'
    return IMAGE_NAME

def serverImageUrl(file_name):
    """ for Unique file name"""
    url = f'{FTP_IMAGE_URL}{file_name}'
    return url

def errorColor(error):
    """ for terminal input error color """
    print(Fore.RED + f'{error}')
    print(Style.RESET_ALL)
    return True

def splitUrlGetFilename(url):
    """ image url split and get file name  """
    return url.split('/')[-1]


def validateState(state):
    """ check valid state methods  """
    # if check state  validate or not
    if state not in list(STATE.keys()):
        raise ValidationError(
            f"{message['invalid_state']}, expected {expectedValue(STATE)}", 422)
        
    else:
        value = 0
        if state == "completed":
            value =  1
        elif state == "pending":
            value = 2
        else:
            value = 3

    return value 

 
def expectedValue(data):
    """ key get values """
    values = []
    for k,v in data.items():
        values.append(f'{v}.({k})')

    return ",".join(values)


def createAccessToken():
    """ create access token w"""
    rand_token = uuid4()

    return f"{str(rand_token)}"


# token validate
def token_required(f):
    """ check token """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"]
        if not token:
            return {
                "message": "Authentication Token is missing!",
                "error": "Unauthorized"
            }, 401
        try:
            current_user = Users.find_by_api_token(token)
            if current_user is None:
                return {
                "message": "Invalid Authentication token!",
                "error": "Unauthorized"
            }, 401
            # if not current_user["active"]:
            #     abort(403)
        except Exception as e:
            return {
                "message": "Something went wrong",
                "error": str(e)
            }, 500

        return f(current_user, **kwargs)

    return decorated

def make_list_context(*, model, db, config, endpoint):
    # --- args ---
    args = request.args
    q_param = config.get("search", {}).get("param", "q")

    # --- base query ---
    query = model.query

    # --- search ---
    qval = (args.get(q_param, "") or "").strip()
    if qval and config.get("search"):
        like = f"%{qval}%"
        ors = [col.ilike(like) for col in config["search"]["columns"]]
        query = query.filter(or_(*ors))

    # --- filters ---
    for f in config.get("filters", []):
        val = (args.get(f["param"], "") or "").strip()
        if not val:
            continue
        if "custom" in f and callable(f["custom"]):
            query = f["custom"](query, val)
        else:
            query = query.filter(f["column"] == val)

    # --- order + fetch ---
    for col in config.get("order_by", []):
        query = query.order_by(col)
    rows = query.all()

    # --- dropdowns ---
    dropdowns = {}
    for key, maker in config.get("dropdowns", {}).items():
        dropdowns[key] = maker(db.session)

    # --- flags ---
    table_is_empty = model.query.count() == 0
    filtered_is_empty = (len(rows) == 0 and not table_is_empty)

    # --- active filters ---
    base_args = args.to_dict()
    active_filters = []
    for key, label in config.get("labels", {}).items():
        val = (args.get(key, "") or "").strip()
        if val:
            args_copy = base_args.copy()
            args_copy.pop(key, None)
            remove_url = url_for(endpoint) + "?" + urlencode(args_copy)
            active_filters.append((label, val, remove_url))

    # --- current selections ---
    current = {k: (args.get(k, "") or "").strip() for k in config.get("labels", {}).keys()}

    return {
        "rows": rows,
        "no_data": table_is_empty,
        "filtered_is_empty": filtered_is_empty,
        "active_filters": active_filters,
        "dropdowns": dropdowns,
        "current": current,
    }

def _apply_search(query, search_cfg, qval):
    if not qval or not search_cfg:
        return query
    like = f"%{qval}%"
    ors = []
    for col in search_cfg["columns"]:
        ors.append(col.ilike(like) if not hasattr(col, "type") else col.ilike(like))
    return query.filter(or_(*ors))

def _apply_filters(query, filters_cfg, args):
    for f in filters_cfg:
        val = (args.get(f["param"], "") or "").strip()
        if not val:
            continue
        if "custom" in f and callable(f["custom"]):
            query = f["custom"](query, val)
        else:
            # default equality filter
            query = query.filter(f["column"] == val)
    return query

def _dropdown_values(dropdowns_cfg, db_session):
    out = {}
    for key, maker in dropdowns_cfg.items():
        out[key] = maker(db_session)
    return out

def _build_remove_url(endpoint, base_args, key):
    args = base_args.copy()
    args.pop(key, None)
    return url_for(endpoint) + "?" + urlencode(args)

def _active_filters(args, labels, endpoint):
    items = []
    base_args = args.to_dict()
    for key, label in labels.items():
        val = (args.get(key, "") or "").strip()
        if val:
            items.append((label, val, _build_remove_url(endpoint, base_args, key)))
    return items

def make_list_context(*, model, db, config, endpoint):
    """
    config = {
      "search": {"param": "q", "columns": [Model.col1, Model.col2, ...]},
      "filters": [
         {"param":"gender","column":Model.gender},
         {"param":"yrgrp","column":Model.yrgrp},
         {"param":"status","column":Model.status},
         {"param":"sped","custom": lambda q,v: ...},
      ],
      "order_by": [Model.colA, Model.colB],
      "dropdowns": {"genders": lambda s: [...], ...},
      "labels": {"q":"Search","gender":"Gender", ...},
    }
    """
    args = request.args
    q_param = config.get("search", {}).get("param", "q")

    # base query
    query = model.query

    # search
    query = _apply_search(
        query,
        config.get("search"),
        (args.get(q_param, "") or "").strip()
    )

    # filters
    query = _apply_filters(query, config.get("filters", []), args)

    # order + fetch
    order_by = config.get("order_by", [])
    for col in order_by:
        query = query.order_by(col)
    rows = query.all()

    # dropdowns
    dropdowns = _dropdown_values(config.get("dropdowns", {}), db.session)

    # chips / flags
    table_is_empty = model.query.count() == 0
    filtered_is_empty = (len(rows) == 0 and not table_is_empty)
    active_filters = _active_filters(args, config.get("labels", {}), endpoint)

    # expose current selections so selects stay selected
    current = {k: (args.get(k, "") or "").strip() for k in config.get("labels", {}).keys()}

    return {
        "rows": rows,
        "no_data": table_is_empty,
        "filtered_is_empty": filtered_is_empty,
        "active_filters": active_filters,
        "dropdowns": dropdowns,
        "current": current,
    }

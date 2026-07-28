from flask import Blueprint, request  # Core Flask routing module and global request context object
from urllib.parse import urlencode  # Utility to convert query parameters into URL-encoded strings
from sqlalchemy import or_, String  # SQLAlchemy logical OR condition and string data type for queries

from apps.helpers import _active_filters, _apply_filters, _apply_search, _dropdown_values  # Internal helper functions for data filtering, search, and dropdown population

# Define a Flask Blueprint for the 'home' application
blueprint = Blueprint(
    # blueprint for apps/home
    'home_blueprint',
    __name__,
    url_prefix=''
)

# Define a helper function to build SQLAlchemy filter predicates
# based on the provided model, configuration, and request arguments
def _build_predicates(*, model, config, args):
    clauses = []

    # --- search ---
    if config.get("search"):
        qparam = config["search"].get("param", "q")
        qval = (args.get(qparam, "") or "").strip()
        if qval:
            like = f"%{qval}%"
            ors = [col.ilike(like) for col in config["search"]["columns"]]
            clauses.append(or_(*ors))

    # --- filters ---
    for f in config.get("filters", []):
        val = (args.get(f["param"], "") or "").strip()
        if not val:
            continue
        # allow special logic via custom_pred
        if "custom_pred" in f and callable(f["custom_pred"]):
            clauses.append(f["custom_pred"](val))
        else:
            clauses.append(f["column"] == val)

    return clauses # Return the list of filter predicates

# Define a function to create the context for rendering a list view 
# based on the model, database session, configuration, and endpoint
def make_list_context(*, model, db, config, endpoint):
    args = request.args
    # 1) build predicates once
    predicates = _build_predicates(model=model, config=config, args=args)

    # 2) apply them to the base query
    query = model.query
    if predicates:
        query = query.filter(*predicates)

    # 3) order + fetch
    for col in config.get("order_by", []):
        query = query.order_by(col)
    rows = query.all()

    # dropdowns
    dropdowns = _dropdown_values(config.get("dropdowns", {}), db.session)

    # chips / flags
    table_is_empty = model.query.count() == 0
    filtered_is_empty = (len(rows) == 0 and not table_is_empty)
    active_filters = _active_filters(args, config.get("labels", {}), endpoint)

    # current selections (keep selects selected)
    current = {k: (args.get(k, "") or "").strip() for k in config.get("labels", {}).keys()}

    # expose predicates for reuse in templates
    return {
        "rows": rows,
        "no_data": table_is_empty,
        "filtered_is_empty": filtered_is_empty,
        "active_filters": active_filters,
        "dropdowns": dropdowns,
        "current": current,
        "predicates": predicates,  # ✅ expose for reuse
    }

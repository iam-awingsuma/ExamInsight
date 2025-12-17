# the code below has been transferred to _init_.py in home
# def make_list_context(*, model, db, config, endpoint):
#     """
#     config = {
#       "search": {"param": "q", "columns": [Model.col1, Model.col2, ...]},
#       "filters": [
#          {"param":"gender","column":Model.gender},
#          {"param":"yrgrp","column":Model.yrgrp},
#          {"param":"status","column":Model.status},
#          {"param":"sped","custom": lambda q,v: ...},
#       ],
#       "order_by": [Model.colA, Model.colB],
#       "dropdowns": {"genders": lambda s: [...], ...},
#       "labels": {"q":"Search","gender":"Gender", ...},
#     }
#     """
#     args = request.args
#     q_param = config.get("search", {}).get("param", "q")

#     # base query
#     query = model.query

#     # search
#     query = _apply_search(
#         query,
#         config.get("search"),
#         (args.get(q_param, "") or "").strip()
#     )

#     # filters
#     query = _apply_filters(query, config.get("filters", []), args)

#     # order + fetch
#     order_by = config.get("order_by", [])
#     for col in order_by:
#         query = query.order_by(col)
#     rows = query.all()

#     # dropdowns
#     dropdowns = _dropdown_values(config.get("dropdowns", {}), db.session)

#     # chips / flags
#     table_is_empty = model.query.count() == 0
#     filtered_is_empty = (len(rows) == 0 and not table_is_empty)
#     active_filters = _active_filters(args, config.get("labels", {}), endpoint)

#     # expose current selections so selects stay selected
#     current = {k: (args.get(k, "") or "").strip() for k in config.get("labels", {}).keys()}

#     return {
#         "rows": rows,
#         "no_data": table_is_empty,
#         "filtered_is_empty": filtered_is_empty,
#         "active_filters": active_filters,
#         "dropdowns": dropdowns,
#         "current": current,
#     }
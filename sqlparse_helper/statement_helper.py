import sqlparse
from sqlparse import sql as C
from sqlparse import tokens as T


def get_select_statement(statement, idx=-1):
    idx, _ = statement.token_next_by(m=(T.Keyword, "from"), idx=idx)
    if idx is not None:
        return statement
    if (t := statement.token_next_by(i=C.Function))[0] is not None:
        return list(t[1].get_sublists())[0]


def get_detailed_type(statement):
    query_type = statement.get_type()
    if query_type in ("UNKNOWN", "SELECT"):
        return query_type
    elif query_type == "INSERT":
        idx, _ = statement.token_next_by(m=(T.Keyword.DML, "insert"))
        idx, _ = statement.token_next_by(i=C.TokenList, idx=idx)
        _, token = statement.token_next(idx)
        if isinstance(token, C.Values):
            return "INSERT INTO VALUES"
        return "INSERT INTO SELECT"
    elif query_type == "CREATE":
        type_1 = ["CREATE"]
        idx, _ = statement.token_next_by(m=(T.Keyword.DDL, "create"))
        while (t := statement.token_next(idx))[0]:
            idx, token = t
            if isinstance(token, C.TokenList):
                break
            type_1.append(token.normalized)
        select_token = statement.token_next_by(t=T.Keyword.DML, idx=idx)[1]
        if {"TEMP", "TABLE"} <= set(type_1):
            query_type = "CREATE TEMP TABLE"
        elif {"TEMP", "VIEW"} <= set(type_1):
            query_type = "CREATE TEMP VIEW"
        elif {"MATERIALIZED", "VIEW"} <= set(type_1):
            query_type = "CREATE MATERIALIZED VIEW"
        elif {"VIEW"} <= set(type_1):
            query_type = "CREATE VIEW"
        elif {"TABLE"} <= set(type_1):
            query_type = "CREATE TABLE"
        else:
            return "UNKNOWN"
        if select_token is not None:
            return query_type + " SELECT"
        else:
            return query_type
    else:
        return "UNKNOWN"


def collect_source_tables(statement):
    return _collect_source_tables_recursively(statement)


def get_with_identifier_dict(statement):
    def get_with_content(idf):
        _, paren = idf.token_next_by(i=C.TokenList)
        return paren

    idx, _ = statement.token_next_by(m=(T.Keyword.CTE, "with"))
    if not idx:
        return {}
    _, idf_ls = statement.token_next_by(i=C.TokenList, idx=idx)
    if isinstance(idf_ls, C.IdentifierList):
        d = {}
        for idf in idf_ls.get_sublists():
            d[idf.get_real_name()] = get_with_content(idf)
        return d
    else:
        idf = idf_ls
        return {idf.get_real_name(): get_with_content(idf)}


def get_dest_tables(statement):
    if statement.get_type() == "INSERT":
        return _get_insert_into_set(statement)
    elif statement.get_type() == "CREATE":
        return _get_create_table_set(statement)
    return set()


def get_from_identifier_list(statement, idx=-1):
    def _get_from_content(statement, idx):
        return statement.token_next(idx)

    statement = get_select_statement(statement)
    idx, _ = statement.token_next_by(m=(T.Keyword, "from"), idx=idx)
    idx, idf_ls = _get_from_content(statement, idx)
    if isinstance(idf_ls, C.IdentifierList):
        return [idf for idf in idf_ls.get_sublists()]
    else:
        return [idf_ls]


def get_join_idfs(statement, idx=-1):
    idx, _ = statement.token_next_by(m=(T.Keyword, "join$", True), idx=idx)
    if not idx:
        return []
    _, idf_ls = statement.token_next_by(i=C.TokenList, idx=idx)
    if isinstance(idf_ls, C.IdentifierList):
        return [idf for idf in idf_ls.get_sublists()]
    else:
        return [idf_ls]


def _get_content_identifiers(statement, idx):
    idx1, t1 = statement.token_next_by(i=C.TokenList, idx=idx)
    idx2, t2 = statement.token_next_by(t=T.Name.Placeholder, idx=idx)
    if idx1 is None and idx2 is None:
        return (None, None)
    elif idx2 is None:
        return (idx1, t1)
    elif idx1 is None:
        return (idx2, C.Identifier([t2]))
    else:
        return (idx1, t1) if idx1 < idx2 else (idx2, C.Identifier([t2]))


def _get_insert_into_set(statement):
    if statement.get_type() != "INSERT":
        return set()

    def get_real_name_of_insert(idf):
        idx, _ = idf.token_next_by(t=T.Whitespace)
        return "".join([t.value for t in idf.tokens[:idx]])

    idx, _ = statement.token_next_by(m=(T.Keyword.DML, "insert"))
    _, idf_ls = _get_content_identifiers(statement, idx)
    if isinstance(idf_ls, C.IdentifierList):
        return {get_real_name_of_insert(idf) for idf in idf_ls.get_sublists()}
    else:
        idf = idf_ls
        return {get_real_name_of_insert(idf)}


def _get_create_table_set(statement):
    if statement.get_type() != "CREATE":
        return set()

    def get_real_name_of_craete(idf):
        idx, _ = idf.token_next_by(t=T.Whitespace)
        return "".join([t.value for t in idf.tokens[:idx]])

    idx, _ = statement.token_next_by(m=(T.Keyword.DDL, "create"))
    _, idf_ls = statement.token_next_by(i=C.TokenList, idx=idx)
    if isinstance(idf_ls, C.IdentifierList):
        return {get_real_name_of_craete(idf) for idf in idf_ls.get_sublists()}
    else:
        idf = idf_ls
        return {get_real_name_of_craete(idf)}


def _collect_source_tables_recursively(statement):
    statement = get_select_statement(statement)
    with_source_tables = _collect_with_source_tables(statement)
    source_tables = _expand_with(
        _collect_source_tables_local(statement), with_source_tables
    )
    return source_tables


def _collect_with_source_tables(statement):
    name2idfs = get_with_identifier_dict(statement)
    return {k: collect_source_tables(v) for k, v in name2idfs.items()}


def _collect_source_tables_local(statement):
    def get_identifier_content(idf):
        return idf.token_first()

    def is_subquery(idf):
        return isinstance(idf, C.TokenList) and isinstance(
            get_identifier_content(idf), C.Parenthesis
        )

    def get_real_name_of_from(idf):
        if sqlparse.utils.imt(idf, t=T.Name.Placeholder):
            return idf.value
        idx, _ = idf.token_next_by(t=T.Whitespace)
        return "".join([t.value for t in idf.tokens[:idx]])

    source_set = set()
    for idf in get_from_identifier_list(statement):
        if is_subquery(idf):
            source_set |= collect_source_tables(get_identifier_content(idf))
        else:
            source_set.add(get_real_name_of_from(idf))

    for idf in get_join_idfs(statement):
        if is_subquery(idf):
            source_set |= collect_source_tables(get_identifier_content(idf))
        else:
            source_set.add(get_real_name_of_from(idf))
    return source_set


def _expand_with(names, with_source_tables):
    new_names = set()
    for name in names:
        if name in with_source_tables:
            new_names |= with_source_tables[name]
        else:
            new_names.add(name)
    return new_names

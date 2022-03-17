import sqlparse

from sqlparse_helper import statement_helper as s


def test_insert_into_01():
    sql = """
        insert into schema.phys_t_1
        with aaa as (
          select * from schema.phys_t_2
        )
        select * from aaa, schema.phys_t_3
        join schema.phys_t_4
        on aaa.x = schema.phys_t_4.x
    """

    statements = sqlparse.parse(sql)
    statement = statements[0]
    ans = s.get_detailed_type(statement)
    assert ans == "INSERT INTO SELECT"
    ans = s.get_dest_tables(statement)
    assert ans == {"schema.phys_t_1"}
    ans = s.collect_source_tables(statement)
    assert ans == {"schema.phys_t_2", "schema.phys_t_3", "schema.phys_t_4"}
    ans = s.get_with_identifier_dict(statement)
    assert isinstance(ans["aaa"], sqlparse.sql.Parenthesis)
    assert ans["aaa"].value[1:-1].strip(), "select * from schema.phys_t_2"
    ans = s.get_from_identifier_list(statement)
    assert ans[0].value == "aaa"
    assert ans[1].value == "schema.phys_t_3"
    ans = s.get_join_idfs(statement)
    assert ans[0].value == "schema.phys_t_4"


def test_insert_into_02():
    sql = """
        with w_1 as (
          with w_2 as (
            with w_3 as (
              select * from (
                select * from schema.phys_a
              ) t
            )
            select * from w_3
          )
          select * from w_2
        )
        select * from w_1
    """

    statements = sqlparse.parse(sql)
    statement = statements[0]
    ans = s.get_detailed_type(statement)
    assert ans == "SELECT"
    ans = s.get_dest_tables(statement)
    assert ans == set()
    ans = s.collect_source_tables(statement)
    assert ans == {"schema.phys_a"}


def test_create_table_01():
    sql = """
        create temp table t_1
        select * from schema.phys_a;
    """

    statements = sqlparse.parse(sql)
    statement = statements[0]
    ans = s.get_detailed_type(statement)
    assert ans == "CREATE TEMP TABLE SELECT"
    ans = s.get_dest_tables(statement)
    assert ans == {"t_1"}
    ans = s.collect_source_tables(statement)
    assert ans == {"schema.phys_a"}


def test_create_table_02():
    sql = """
        create temp table t_1 (
          id int,
          aaa string
        );
    """

    statements = sqlparse.parse(sql)
    statement = statements[0]
    ans = s.get_detailed_type(statement)
    assert ans == "CREATE TEMP TABLE"


if __name__ == "__main__":
    test_insert_into_01()
    test_insert_into_02()
    test_create_table_01()
    test_create_table_02()

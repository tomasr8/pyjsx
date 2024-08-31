# coding: jsx
from pyjsx import jsx, JSX


def make_header(names: list[str]) -> JSX:
    return (
        <thead>
            <tr>
                {<th>{name}</th> for name in names}
            </tr>
        </thead>
    )


def make_body(rows: list[list[str]]) -> JSX:
    return (
        <tbody>
            {
                <tr>
                    {<td>{cell}</td> for cell in row}
                </tr>
                for row in rows
            }
        </tbody>
    )


def make_table() -> JSX:
    columns = ["Name", "Age"]
    rows = [["Alice", "34"], ["Bob", "56"]]

    return (
        <table>
            {make_header(columns)}
            {make_body(rows)}
        </table>
    )

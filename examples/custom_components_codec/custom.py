# coding: jsx
from pyjsx import jsx, JSX


def Header(children, style=None, **rest) -> JSX:
    return <h1 style={style}>{children}</h1>


def Main(children, **rest) -> JSX:
    return <main>{children}</main>


def App() -> JSX:
    return (
        <div>
            <Header style={{"color": "red"}}>Hello, world!</Header>
            <Main>
                <p>This was rendered with PyJSX!</p>
            </Main>
        </div>
    )

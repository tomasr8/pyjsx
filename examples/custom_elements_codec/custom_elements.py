# coding: jsx
from pyjsx import jsx, JSX


def App() -> JSX:
    return (
        <>
            <site-header>
                <h1>Hello, world!</h1>
            </site-header>
            <main-content>
                <p>This is a custom elements example.</p>
            </main-content>
            <site-footer>
                <p>© 2025 My Company</p>
            </site-footer>
        </>
    )

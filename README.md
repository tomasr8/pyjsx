<p align="center">
  <img src="logo_bungee_tint.svg" />
</p>

# PyJSX - Write JSX directly in Python
[![PyPI - Version](https://img.shields.io/pypi/v/python-jsx)](https://pypi.org/project/python-jsx/)

### 👉 We now have a [VSCode plugin](https://marketplace.visualstudio.com/items?itemName=tomasr8.pyjsx)!

```python
from pyjsx import jsx, JSX

def Header(style, children) -> JSX:
    return <h1 style={style}>{children}</h1>

def Main(children) -> JSX:
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
```

## Installation

Get it via pip:

```sh
pip install python-jsx
```

## Minimal example (using the `coding` directive)

> [!TIP]
> There are more examples available in the [examples folder](examples).

There are two supported ways to seamlessly integrate JSX into your codebase.
One is by registering a custom codec shown here and the other by using a custom import hook shown [below](#minimal-example-using-an-import-hook).

```python
# hello.py
# coding: jsx
from pyjsx import jsx

def hello():
    print(<h1>Hello, world!</h1>)
```

```python
# main.py
import pyjsx.auto_setup

from hello import hello

hello()
```

```sh
$ python main.py
<h1>Hello, word!</h1>
```

Each file containing JSX must contain two things:

- `# coding: jsx` directive - This tells Python to let our library parse the
  file first.
- `from pyjsx import jsx` import. PyJSX transpiles JSX into `jsx(...)` calls so
  it must be in scope.

To run a file containing JSX, the `jsx` codec must be registered first which can
be done with `import pyjsx.auto_setup`. This must occur before importing
any other file containing JSX.

## Minimal example (using an import hook)

> [!TIP]
> There are more examples available in the [examples folder](examples).

```python
# hello.px
from pyjsx import jsx

def hello():
    print(<h1>Hello, world!</h1>)
```

```python
# main.py
import pyjsx.auto_setup

from hello import hello

hello()
```

```sh
$ python main.py
<h1>Hello, word!</h1>
```

Each file containing JSX must contain two things:

- The file extension must be `.px`
- `from pyjsx import jsx` import. PyJSX transpiles JSX into `jsx(...)` calls so
  it must be in scope.

To be able to import `.px`, the import hook must be registered first which can
be done with `import pyjsx.auto_setup` (same as for the codec version). This must occur before importing any other file containing JSX.

## Supported grammar

The full [JSX grammar](https://facebook.github.io/jsx/) is supported.
Here are a few examples:

### Normal and self-closing tags

```python
x = <div></div>
y = <img />
```

### Props

```python
<a href="example.com">Click me!</a>
<div style={{"color": "red"}}>This is red</div>
<span {...props}>Spread operator</span>
```

### Nested expressions

```python
<div>
    {[<p>Row: {i}</p> for i in range(10)]}
</div>
```

### Fragments

```python
fragment = (
    <>
        <p>1st paragraph</p>
        <p>2nd paragraph</p>
    </>
)
```

### Custom components

A custom component can be any function that takes `**kwargs` and
returns JSX or a plain string. The special prop `children` is a list
containing the element's children.

```python
def Header(children, **rest):
    return <h1>{children}</h1>

header = <Header>Title</Header>
print(header)
```

### Preventing HTML escaping

By default, PyJSX escapes all string content to prevent XSS attacks. To render raw HTML, wrap strings with `HTMLDontEscape`:

```python
from pyjsx import jsx, HTMLDontEscape

safe_html = HTMLDontEscape("<strong>Bold text</strong>")
element = <div>{safe_html}</div>
print(element)  # <div><strong>Bold text</strong></div>
```

## VS Code support

PyJSX comes with a [VS Code plugin](https://marketplace.visualstudio.com/items?itemName=tomasr8.pyjsx) that provides syntax highlighting.

## Type checking

PyJSX includes a plugin that allows mypy to parse files with JSX in them. To
use it, add `pyjsx.mypy` to the `plugins` list in your [mypy configuration
file][mypy]. For example, in `mypy.ini`:

```ini
[mypy]
plugins = pyjsx.mypy
```

Or in `pyproject.toml`:

```toml
[tool.mypy]
plugins = ["pyjsx.mypy"]
```

[mypy]: https://mypy.readthedocs.io/en/stable/config_file.html

## Prior art

Inspired by [packed](https://github.com/michaeljones/packed) and
[pyxl4](https://github.com/pyxl4/pyxl4).

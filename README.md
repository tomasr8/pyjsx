<p align="center">
  <img src="logo_bungee_tint.svg" />
</p>

# PyJSX - Write JSX directly in Python

```python
# coding: jsx
from pyjsx import jsx

def get_body(title, href):
    return (
        <body>
            <h1>{title}</h1>
            <p>
                <a href={href}>"Click me!"</a>
            </p>
        </body>
    )

print(get_body("Title", "example.com"))
```

language spec:" https://facebook.github.io/jsx/

## Installation

Get it via pip:

```sh
pip install jsx-python
```

## Minimal example

```python
# hello.py
# coding: jsx
from pyjsx import jsx

def hello():
    print(<h1>Hello, world!</>)
```

```python
# main.py
from pyjsx import auto_setup

from hello import hello

hello()
```

```sh
$ python main.py
<h1>Hello, word!</h1>
```

> [!TIP]
> There are more examples available in the [examples folder](examples).

Each file containing JSX must contain two things:

- `# coding: jsx` directive - This tells Python to let our library parse the
  file first.
- `from pyjsx import jsx` import. PyJSX transpiles JSX into `jsx(...)` calls so
  it must be in scope.

To run a file containing JSX, the `jsx` codec must be registered first which can
be done with `from pyjsx import auto_setup`. This must occur before importing
any other file containing JSX.

## Supported grammar

In principle the full [JSX grammar](https://facebook.github.io/jsx/) except for
some obscure cases is supported. Here's a non-exhaustive list:

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

A custom component can be any function that takes a single argument props and
returns JSX or a string.

```python
def Header(props):
    return <h1>{props["children"]}</h1>

header = <Header>Title</Header>
print(header)
```

## Prior art

Inspired by [packed](https://github.com/michaeljones/packed) and
[pyxl4](https://github.com/pyxl4/pyxl4).

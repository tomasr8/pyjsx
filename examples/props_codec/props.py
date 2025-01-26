# coding: jsx
from pyjsx import jsx, JSX


def Card(rounded=False, raised=False, image=None, children=None, **rest) -> JSX:
    style = {
        "border-radius": "5px" if rounded else 0,
        "box-shadow": "0 2px 4px rgba(0, 0, 0, 0.1)" if raised else "none",
    }
    return (
        <div style={style}>
            {image}
            {children}
        </div>
    )


def Image(src, alt, **rest) -> JSX:
    return <img src={src} alt={alt} />


def App() -> JSX:
    return (
        <div>
            <Card rounded raised image={<Image src="dog.jpg" alt="A picture of a dog" />}>
                <h1>Card title</h1>
                <p>Card content</p>
            </Card>
            <Card rounded raised={False} disabled image={<Image src="cat.jpg" alt="A picture of a cat" />}>
                <h1>Card title</h1>
                <p>Card content</p>
            </Card>
            <Card rounded raised={False}>
                <h1>Card title</h1>
                <p>Card content</p>
            </Card>
        </div>
    )

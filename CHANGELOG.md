# Change Log

## Unreleased

- Nothing yet

## 0.3.0

- Mypy plugin ([#8](https://github.com/tomasr8/pyjsx/pull/8), thanks @wbadart)
- Support for custom tags ([#11](https://github.com/tomasr8/pyjsx/pull/11), thanks @mplemay)

## 0.2.0

Officially adds support for an import hook mechanism. This allows you to create .px files containing JSX which can be imported as if they were regular Python files.

Note that this is in addition to the # coding: jsx mechanism - you can use either. See the examples in the readme for more details.

Using a separate file extension for pyjsx will make it easier to add IDE support later on.

## 0.1.0

- Initial release

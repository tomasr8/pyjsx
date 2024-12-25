from pathlib import Path

from pyjsx.source_maps.source_maps import convert_mappings, generate_source_map
from pyjsx.transpiler import Parser


# source = """\
# <p {...rest}>
#     <h1>Title</h1>
#     <h2>Subtitle</h2>
#     {foo}
# </p>"""

source = """\
<p>
    lorem ipsum
    <b>blah</b>
    blah
    {foo}
</p>"""


p = Parser(source)
ast = p.parse()

# tr = Transpiler(ast)
# tr.transpile()

transpiled, source_map = ast.transpile()
for m in source_map:
    print(m, source[m.original_offset :])
# print(source_map)
source_map = convert_mappings(source_map, source, transpiled, name="main.px")
generated = generate_source_map(source_map, sources=["main.px"], sources_content=[source], file="main.px")
# print(transpiled)


Path("main.px.map").write_text(generated, "utf-8")
Path("main.px").write_text(transpiled, "utf-8")

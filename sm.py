from pathlib import Path

from pyjsx.source_maps.source_maps import Mapping, generate_source_map


mappings = [
    Mapping(generated_line=1, generated_column=0, source="main.px", original_line=1, original_column=0),
    Mapping(generated_line=2, generated_column=1, source="main.px", original_line=2, original_column=0),
]

Path("main2.px.map").write_text(generate_source_map(mappings, ["main.px"]), "utf-8")

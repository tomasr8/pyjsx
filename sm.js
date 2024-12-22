import fs from "fs";
import { SourceMapGenerator } from "source-map";

var map = new SourceMapGenerator({
  file: "main.py",
});

map.setSourceContent("main.px", "x = 1, 2\ny = 2");
map.setSourceContent("main1.px", "x = 1, 2\ny = 2");
map.setSourceContent("main2.px", "x = 1, 2\ny = 2");
map.setSourceContent("main3.px", "x = 1, 2\ny = 2");

map.addMapping({
  generated: {
    line: 1,
    column: 0,
  },
  source: "main.px",
  original: {
    line: 1,
    column: 0,
  },
});

map.addMapping({
  generated: {
    line: 1,
    column: 5,
  },
  source: "main.px",
  original: {
    line: 1,
    column: 10,
  },
});

map.addMapping({
  generated: {
    line: 2,
    column: 0,
  },
  source: "main.px",
  original: {
    line: 2,
    column: 0,
  },
});

map.addMapping({
  generated: {
    line: 3,
    column: 0,
  },
  source: "main.px",
  original: {
    line: 3,
    column: 0,
  },
});

map.addMapping({
  generated: {
    line: 3,
    column: 5,
  },
  source: "main.px",
  original: {
    line: 3,
    column: 10,
  },
});

// map.addMapping({
//   generated: {
//     line: 2,
//     column: 1,
//   },
//   source: "main.px",
//   original: {
//     line: 2,
//     column: 0,
//   },
// });

console.log(JSON.parse(map.toString()).mappings);
fs.writeFileSync("main.px.map", map.toString());

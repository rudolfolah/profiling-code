## Node.js profiling tools

* [Profiling Node.js Applications](https://nodejs.org/en/learn/getting-started/profiling)
* [Flame graphs](https://nodejs.org/en/learn/diagnostics/flame-graphs)
* [Linux Perf](https://nodejs.org/en/learn/diagnostics/poor-performance/using-linux-perf)
* [Heap Profiler](https://nodejs.org/en/learn/diagnostics/memory/using-heap-profiler/)
* [Heap Snapshot](https://nodejs.org/en/learn/diagnostics/memory/using-heap-snapshot/)
* [GC (Garbage Collection) Traces](https://nodejs.org/en/learn/diagnostics/memory/using-gc-traces)
* [Visual Studio Code: Performance Profiling JavaScript](https://code.visualstudio.com/docs/nodejs/profiling)



### [Webpack](https://webpack.js.org/)

```shell
NODE_ENV=production node --cpu-prof ./node_modules/webpack-cli/bin.js
NODE_ENV=production node --heap-prof ./node_modules/webpack-cli/bin.js
NODE_ENV=production node --expose-gc ./node_modules/webpack-cli/bin.js
node --trace-gc --max-old-space-size=4000 ./node_modules/webpack-cli/bin.js
```

### [Jest](https://jestjs.io/)

```shell
node --expose-gc --no-compilation-cache ./node_modules/jest-cli/bin/jest.js --logHeapUsage
node --heap-prof --expose-gc --no-compilation-cache ./node_modules/jest-cli/bin/jest.js --logHeapUsage
```

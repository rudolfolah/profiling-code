# JavaScript and Node.js Performance Profiling Skill

This skill provides expert guidance and actionable commands for profiling JavaScript and Node.js applications. It covers CPU profiling, memory analysis, heap snapshots, and garbage collection tracing, with specific integrations for popular tools like Webpack and Jest.

## Quick Start: Built-in Node.js Profilers

Node.js (v12+) includes powerful profilers that don't require external packages.

### CPU Profiling
Use this to identify "hot" functions and execution bottlenecks.
```bash
node --cpu-prof your-app.js
```
- **Analysis**: Upload the generated `.cpuprofile` file to **Chrome DevTools** (Performance tab -> Load profile).

### Heap Profiling
Use this to analyze memory allocation over time and find leaks.
```bash
node --heap-prof your-app.js
```
- **Analysis**: Upload the generated `.heapprofile` file to **Chrome DevTools** (Memory tab -> Load).

### GC Tracing
Monitor Garbage Collection activity to identify "GC thrashing" or memory pressure.
```bash
node --trace-gc your-app.js
```

---

## Programmatic Profiling

Sometimes you need to trigger profiling from within the code, for example, on a specific event or via a signal.

### Programmatic Heap Snapshot
Generate a heap snapshot at a specific point in execution.
```javascript
const v8 = require('v8');
const fs = require('fs');

// Generate and save to file
const snapshotPath = `./heap-${Date.now()}.heapsnapshot`;
const stream = v8.getHeapSnapshot();
stream.pipe(fs.createWriteStream(snapshotPath));

console.log(`Snapshot saved to ${snapshotPath}`);
```

### CPU Profiling with `v8-profiler-next`
For more control over CPU profiling (start/stop) without restarting the process.
```javascript
const profiler = require('v8-profiler-next');
const fs = require('fs');

const profileName = 'my-profile';

// Start profiling
profiler.startProfiling(profileName, true);

// Stop after 5 seconds
setTimeout(() => {
  const profile = profiler.stopProfiling(profileName);
  profile.export((error, result) => {
    fs.writeFileSync(`./${profileName}.cpuprofile`, result);
    profile.delete();
    console.log('Profile exported');
  });
}, 5000);
```

### Performance Measurement with `perf_hooks`
High-resolution timestamps and markers for specific code blocks.
```javascript
const { performance, PerformanceObserver } = require('perf_hooks');

const obs = new PerformanceObserver((items) => {
  items.getEntries().forEach((entry) => {
    console.log(`${entry.name}: ${entry.duration}ms`);
  });
});
obs.observe({ entryTypes: ['measure'] });

performance.mark('start-op');
// ... some work ...
performance.mark('end-op');
performance.measure('Operation Duration', 'start-op', 'end-op');
```

---

## Advanced GC and Memory Management

### Manual Garbage Collection
Trigger GC manually (requires `node --expose-gc`).
```javascript
if (global.gc) {
  console.log('Starting manual GC...');
  global.gc();
  console.log('GC complete.');
} else {
  console.warn('GC not exposed. Run with --expose-gc');
}
```

### Monitoring Memory Usage
A simple script to log memory usage periodically.
```javascript
setInterval(() => {
  const usage = process.memoryUsage();
  console.log({
    rss: `${(usage.rss / 1024 / 1024).toFixed(2)} MB`,
    heapTotal: `${(usage.heapTotal / 1024 / 1024).toFixed(2)} MB`,
    heapUsed: `${(usage.heapUsed / 1024 / 1024).toFixed(2)} MB`,
    external: `${(usage.external / 1024 / 1024).toFixed(2)} MB`,
  });
}, 10000);
```

---

## Tool-Specific Profiling

### Webpack Build Profiling
Optimize your build times and memory usage during compilation.
```bash
# CPU Profile of Webpack build
NODE_ENV=production node --cpu-prof ./node_modules/webpack-cli/bin.js

# Heap Profile of Webpack build
NODE_ENV=production node --heap-prof ./node_modules/webpack-cli/bin.js

# Trace GC with increased heap size
node --trace-gc --max-old-space-size=4000 ./node_modules/webpack-cli/bin.js
```

### Jest Test Profiling
Identify slow or memory-hungry test suites.
```bash
# Log heap usage during tests
node --expose-gc --no-compilation-cache ./node_modules/jest-cli/bin/jest.js --logHeapUsage

# Combined Heap Profile and Log
node --heap-prof --expose-gc --no-compilation-cache ./node_modules/jest-cli/bin/jest.js --logHeapUsage
```

### Clinic.js
A powerful suite of tools for diagnosing Node.js performance issues.
```bash
# Install clinic
npm install -g clinic

# Clinic Doctor: General health check
clinic doctor -- node your-app.js

# Clinic Flame: Detailed flamegraph
clinic flame -- node your-app.js

# Clinic Bubbleprof: Visualize async delays
clinic bubbleprof -- node your-app.js
```

---

## Profiling Techniques Reference

| Tool/Flag | Best For | Output Format | Analysis Tool |
|-----------|----------|---------------|---------------|
| `--cpu-prof` | Execution bottlenecks | `.cpuprofile` | Chrome DevTools Performance |
| `--heap-prof` | Memory allocation | `.heapprofile` | Chrome DevTools Memory |
| `--heapsnapshot` | Point-in-time memory | `.heapsnapshot` | Chrome DevTools Memory |
| `--trace-gc` | GC frequency/latency | Stdout logs | Text analysis / GCView |
| `--expose-gc` | Manual GC for testing | N/A | `global.gc()` in code |
| `clinic` | Multi-faceted analysis | HTML/SVG | Browser |
